# AgentOS — agent-setup

Multi-Layer Agentic OS for Claude Code. Token-efficient, tiered, parallel by default.

## Architecture

```
src/
  orchestrator.py  — Tiered orchestrator with auto-classification & parallel execution
  context.py       — Context budget manager, result compression, selective file loading
  services.py      — MCP service registry with health checks
  mcp_n8n.py       — n8n MCP server (7 tools: list/get/create/update/activate/trigger/executions)
  agents/
    researcher.py  — Web research agent (WebSearch + WebFetch)
  tools/
    custom_tools.py — Project tools MCP server (log_decision, get_project_context, audit)
  hooks/
    audit.py       — PostToolUse audit logging with sensitive key masking
```

## Model Tiers

| Tier | Model | Use Case |
|------|-------|----------|
| t0 | claude-haiku-4-5-20251001 | Lookups, grep, structure mapping |
| t1 | claude-sonnet-4-6 | Standard edits, reviews, features |
| t2 | claude-opus-4-6 | Complex reasoning, architecture |

## Usage

```bash
# Auto-classified task
python3 src/orchestrator.py "Analyze this project"

# Force tier
python3 src/orchestrator.py --tier t0 "Find all API endpoints"

# Parallel tasks
python3 src/orchestrator.py --parallel "Analyze structure" "Review security"

# Workflow templates
python3 src/orchestrator.py --template analyze
python3 src/orchestrator.py --template build "Add auth middleware"
python3 src/orchestrator.py --template research "Claude Agent SDK patterns"

# Service health
python3 src/services.py --health
python3 src/services.py --list
```

## Token Budget
- Subagent results: max 500 words, auto-compressed
- Synthesis prompts: max 4000 tokens
- Project snapshots: minimal markers only
- File loading: section-based, not full files
