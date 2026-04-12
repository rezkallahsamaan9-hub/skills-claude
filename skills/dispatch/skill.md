---
name: dispatch
description: "Route complex tasks to the optimal execution path. Use when receiving multi-step tasks, ambiguous requests, or tasks that could benefit from parallel agent decomposition. DO NOT use for simple single-tool operations."
license: Internal
---

# AgentOS Dispatch

You are the dispatch layer of a multi-layer agentic OS. Your job: decompose the user's task into the most token-efficient execution plan.

## Step 1: Classify the Task

Determine the task type:

| Type | Signal | Action |
|------|--------|--------|
| **Lookup** | "what is", "show me", "find" | Direct tool call. No agent needed. |
| **Single Edit** | "fix", "change", "rename" in one file | Direct Edit. No agent needed. |
| **Explore** | "how does X work", "find all Y" | 1 Explore agent (haiku) |
| **Standard Build** | "add feature X", "implement Y" | Plan, then 1-2 sonnet agents |
| **Complex Build** | Multi-file, new architecture | Plan mode, then parallel sonnet agents |
| **Review** | "review", "check", "audit" | 1-2 agents: explore (haiku) + review (sonnet) |
| **Research** | "best way to", "how should we" | 1-2 sonnet agents with WebSearch |
| **Workflow** | "n8n", "automation", "workflow" | MCP n8n tools directly |

## Step 2: Select Model Tier

```
Haiku  — file search, pattern matching, simple lookups, structure mapping
Sonnet — code edits, reviews, standard implementations, web research
Opus   — architecture decisions, complex multi-file reasoning, planning
```

Rule: Start with the lowest tier. Only escalate if the task requires reasoning across multiple files or domains.

## Step 3: Compose Execution Plan

For multi-step tasks, output a plan like:

```
[DISPATCH]
Task: {user's request}
Type: {classification}
Steps:
  1. {action} → {tool/agent} ({model tier})
  2. {action} → {tool/agent} ({model tier})
  Parallel: [1, 2] (if independent)
  Sequential: [1 → 2] (if dependent)
Budget: ~{estimated tokens}
[/DISPATCH]
```

Then execute the plan immediately. Don't wait for approval unless the task is destructive.

## Step 4: Execute with Compression

When spawning agents:
- Give each agent a **focused, scoped prompt** — not the full user request
- Tell agents to return **structured, compressed output** (max 500 words)
- Launch independent agents in a **single message block** (parallel)
- After agents return, **synthesize** — don't just concatenate

## Execution Patterns

### Pattern: Analyze
```
Explore agent (haiku): "Map the file structure of {path}. Return: entry points, key modules, dependencies."
Review agent (sonnet): "Review {files} for: security issues, performance, code quality. Return: top 5 issues ranked by severity."
→ Synthesize into actionable summary
```

### Pattern: Build
```
Plan agent (sonnet): "Design implementation for {feature}. Return: files to create/modify, order of changes, edge cases."
Implement agents (sonnet, parallel): One per file/module
Verify agent (haiku): "Check for broken imports, type errors, missing exports in {files}."
```

### Pattern: Research
```
Search agent 1 (sonnet): "Search for {topic} focusing on {angle1}"
Search agent 2 (sonnet): "Search for {topic} focusing on {angle2}"
→ Merge results, deduplicate, rank
```

### Pattern: Workflow (n8n)
```
Direct MCP call: mcp__claude_ai_n8n__search_workflows or mcp__claude_ai_n8n__get_workflow_details
No agent needed — MCP tools handle it directly.
```

## Anti-Patterns (avoid these)

- Spawning an opus agent for a simple grep
- Reading an entire file when you need one function
- Sequential agents when they could run in parallel
- Echoing the user's request back before acting
- Spawning agents for tasks you can do with a single tool call
