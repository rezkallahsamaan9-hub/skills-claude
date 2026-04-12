"""
AgentOS — Multi-Layer Orchestrator
====================================
Tiered agent workers with model selection, parallel execution,
and compressed handoffs for token efficiency.

Usage:
    # Single task
    python3 src/orchestrator.py "Analysiere dieses Projekt"

    # With tier override
    python3 src/orchestrator.py --tier t1 "Add error handling to auth.py"

    # Parallel tasks
    python3 src/orchestrator.py --parallel "Analyze structure" "Review security" "Plan refactor"
"""

from __future__ import annotations

import anyio
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    AssistantMessage,
    TextBlock,
    SystemMessage,
    CLINotFoundError,
    CLIConnectionError,
    ProcessError,
)


# ─── Model Tiers ────────────────────────────────────────────────────────────

TIERS = {
    "t0": "claude-haiku-4-5-20251001",   # Lookups, grep, simple transforms
    "t1": "claude-sonnet-4-6",            # Standard edits, reviews, features
    "t2": "claude-opus-4-6",              # Complex reasoning, architecture
}

WORKSPACE = Path(__file__).parent.parent / "workspace"
AUDIT_LOG = WORKSPACE / "audit.log"


# ─── Subagent Definitions (tiered) ──────────────────────────────────────────

def make_agents(tier: str = "t0") -> dict[str, AgentDefinition]:
    """Create agent definitions at the specified tier."""
    return {
        "explorer": AgentDefinition(
            description="Maps codebase structure, finds entry points, traces dependencies.",
            prompt="""You are a code explorer. Your job:
1. Map file/folder structure
2. Identify entry points and key modules
3. Trace import chains and dependencies
Return a STRUCTURED summary (max 300 words). Use bullet points.""",
            tools=["Read", "Glob", "Grep"],
        ),
        "reviewer": AgentDefinition(
            description="Reviews code for security, performance, and quality issues.",
            prompt="""You are a senior code reviewer. Focus on:
1. Security vulnerabilities (injection, XSS, unsafe inputs)
2. Performance bottlenecks
3. Code quality and maintainability
Return TOP 5 issues ranked by severity. Include file:line references.
Max 400 words.""",
            tools=["Read", "Glob", "Grep"],
        ),
        "planner": AgentDefinition(
            description="Designs implementation plans with concrete steps.",
            prompt="""You are a software architect. Your job:
1. Break the task into ordered steps
2. Identify file changes needed per step
3. Flag risks and alternatives
Return a NUMBERED plan. Max 400 words.""",
            tools=["Read", "Glob", "Grep"],
        ),
        "builder": AgentDefinition(
            description="Implements code changes based on a plan.",
            prompt="""You are an implementation agent. You receive a specific, scoped task.
1. Read the relevant files first
2. Make the minimal changes needed
3. Verify imports and references are correct
Be precise. Don't over-engineer.""",
            tools=["Read", "Glob", "Grep", "Edit", "Write", "Bash"],
        ),
        "verifier": AgentDefinition(
            description="Verifies changes don't break anything — checks imports, types, tests.",
            prompt="""You are a verification agent. After changes are made:
1. Check for broken imports
2. Verify exported interfaces match consumers
3. Run relevant tests if available
Return PASS/FAIL with details. Max 200 words.""",
            tools=["Read", "Glob", "Grep", "Bash"],
        ),
    }


# ─── Task Classifier ────────────────────────────────────────────────────────

def classify_task(task: str) -> tuple[str, str]:
    """
    Classify a task and return (task_type, recommended_tier).
    Simple heuristic — the dispatch skill does the smart routing.
    """
    task_lower = task.lower()

    # Lookup patterns
    if any(w in task_lower for w in ["find", "search", "where is", "show me", "list"]):
        return "lookup", "t0"

    # Review patterns
    if any(w in task_lower for w in ["review", "audit", "check", "security"]):
        return "review", "t1"

    # Research patterns
    if any(w in task_lower for w in ["research", "best practice", "how should", "compare"]):
        return "research", "t1"

    # Build patterns
    if any(w in task_lower for w in ["implement", "add", "create", "build", "refactor"]):
        return "build", "t1"

    # Analysis patterns
    if any(w in task_lower for w in ["analyze", "explain", "understand", "how does"]):
        return "analyze", "t0"

    # Debug/test patterns
    if any(w in task_lower for w in ["debug", "fix", "test", "bug"]):
        return "review", "t1"

    # Complex patterns (escalate to opus)
    if any(w in task_lower for w in ["architect", "design", "migrate", "rewrite"]):
        return "complex", "t2"

    return "general", "t1"


# ─── Orchestrator ────────────────────────────────────────────────────────────

async def run_task(
    task: str,
    tier: str | None = None,
    cwd: str = ".",
    max_turns: int = 20,
    quiet: bool = False,
) -> str:
    """
    Execute a task with automatic tier selection and agent routing.

    Args:
        task: The task description
        tier: Override model tier (t0/t1/t2). Auto-detected if None.
        cwd: Working directory
        max_turns: Max conversation turns
        quiet: Suppress progress output
    """
    task_type, auto_tier = classify_task(task)
    tier = tier or auto_tier
    model = TIERS[tier]

    if not quiet:
        print(f"\n{'─'*60}")
        print(f"Task: {task}")
        print(f"Type: {task_type} | Tier: {tier} ({model})")
        print(f"{'─'*60}\n")

    # Select which agents to expose based on task type
    agent_map = {
        "lookup": ["explorer"],
        "analyze": ["explorer", "reviewer"],
        "review": ["explorer", "reviewer"],
        "research": ["explorer"],
        "build": ["planner", "builder", "verifier"],
        "complex": ["explorer", "planner", "builder", "reviewer", "verifier"],
        "general": ["explorer", "planner", "builder"],
    }

    all_agents = make_agents(tier)
    active_agents = {k: v for k, v in all_agents.items() if k in agent_map.get(task_type, [])}

    # Select tools based on task type
    base_tools = ["Read", "Glob", "Grep"]
    if task_type in ("build", "complex"):
        base_tools += ["Edit", "Write", "Bash"]
    if task_type == "research":
        base_tools += ["WebSearch", "WebFetch"]
    if active_agents:
        base_tools.append("Agent")

    result_text = ""
    session_id = None

    system_prompt = f"""You are an AgentOS orchestrator. Task type: {task_type}.

Available subagents: {', '.join(active_agents.keys()) if active_agents else 'none'}

Rules:
- Launch independent agents in PARALLEL (single message block)
- Each agent returns compressed results (max 500 words)
- Synthesize agent results into a coherent answer
- Don't echo the user's request. Go straight to work.
- Be concise. Max 800 words total response."""

    try:
        async for message in query(
            prompt=task,
            options=ClaudeAgentOptions(
                model=model,
                cwd=cwd,
                allowed_tools=base_tools,
                agents=active_agents if active_agents else None,
                permission_mode="acceptEdits",
                system_prompt=system_prompt,
                max_turns=max_turns,
            ),
        ):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id", "unknown")
                if not quiet:
                    print(f"Session: {session_id}\n")

            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        if not quiet:
                            print(block.text, end="", flush=True)

            elif isinstance(message, ResultMessage):
                result_text = message.result
                if not quiet:
                    cost_info = ""
                    if hasattr(message, "usage"):
                        cost_info = f" | Tokens: {message.usage}"
                    print(f"\n\n{'─'*60}")
                    print(f"Done | Turns: {message.num_turns} | Tier: {tier}{cost_info}")

    except CLINotFoundError:
        print("Claude Code CLI not found. Install: pip install claude-agent-sdk")
    except CLIConnectionError as e:
        print(f"Connection error: {e}")
    except ProcessError as e:
        print(f"Process error: {e}")

    # Audit log
    _log_audit(task, task_type, tier, session_id)

    return result_text


def _log_audit(task: str, task_type: str, tier: str, session_id: str | None):
    """Append to audit log."""
    WORKSPACE.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task[:200],
        "type": task_type,
        "tier": tier,
        "session": session_id,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── Parallel Runner ────────────────────────────────────────────────────────

async def run_parallel(
    tasks: list[str],
    tier: str | None = None,
    cwd: str = ".",
) -> list[str]:
    """Run multiple independent tasks in parallel."""
    print(f"\nStarting {len(tasks)} parallel tasks...\n")

    async with anyio.create_task_group() as tg:
        results = [None] * len(tasks)

        async def _run(idx, task):
            results[idx] = await run_task(task, tier=tier, cwd=cwd, quiet=True)

        for i, task in enumerate(tasks):
            tg.start_soon(_run, i, task)

    return results


# ─── Workflow Templates ──────────────────────────────────────────────────────

async def analyze(path: str = ".") -> str:
    """Analyze template: explore + review in parallel."""
    results = await run_parallel(
        [
            f"Map the file structure of {path}. Return: entry points, key modules, dependencies.",
            f"Review code in {path} for security issues, performance, code quality. Return top 5 issues.",
        ],
        tier="t0",
        cwd=path,
    )
    return "\n\n---\n\n".join(r for r in results if r)


async def build(feature: str, cwd: str = ".") -> str:
    """Build template: plan → implement → verify."""
    plan = await run_task(
        f"Design implementation plan for: {feature}",
        tier="t1", cwd=cwd, max_turns=5,
    )
    impl = await run_task(
        f"Implement this plan:\n{plan[:2000]}",
        tier="t1", cwd=cwd, max_turns=15,
    )
    verify = await run_task(
        f"Verify the changes just made for: {feature}. Check imports, types, tests.",
        tier="t0", cwd=cwd, max_turns=5,
    )
    return f"PLAN:\n{plan}\n\nIMPLEMENTATION:\n{impl}\n\nVERIFICATION:\n{verify}"


async def research(topic: str) -> str:
    """Research template: parallel search from multiple angles."""
    results = await run_parallel(
        [
            f"Search for: {topic}. Focus on official docs and recent articles (2025-2026).",
            f"Search for: {topic}. Focus on community experiences, gotchas, and alternatives.",
        ],
        tier="t1",
    )
    return "\n\n---\n\n".join(r for r in results if r)


# ─── CLI Entry Point ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgentOS Orchestrator")
    parser.add_argument("tasks", nargs="+", help="Task(s) to execute")
    parser.add_argument("--tier", choices=["t0", "t1", "t2"], default=None)
    parser.add_argument("--parallel", action="store_true", help="Run tasks in parallel")
    parser.add_argument("--template", choices=["analyze", "build", "research"], default=None)
    parser.add_argument("--cwd", default=os.getcwd())
    args = parser.parse_args()

    if args.template == "analyze":
        anyio.run(analyze, args.cwd)
    elif args.template == "build":
        anyio.run(build, " ".join(args.tasks), args.cwd)
    elif args.template == "research":
        anyio.run(research, " ".join(args.tasks))
    elif args.parallel:
        anyio.run(run_parallel, args.tasks, args.tier, args.cwd)
    else:
        task = " ".join(args.tasks)
        anyio.run(run_task, task, args.tier, args.cwd)


if __name__ == "__main__":
    main()
