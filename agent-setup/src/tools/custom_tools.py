"""
Custom MCP Tools
-----------------
Eigene Tools die als MCP-Server registriert werden.
Erweiterbar für projektspezifische Integrationen.
"""

import json
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import tool, create_sdk_mcp_server


# ─── Tool-Definitionen ────────────────────────────────────────────────────────

@tool(
    "log_decision",
    "Loggt eine wichtige Entscheidung oder Erkenntnis ins Projektlog",
    {"decision": str, "context": str, "impact": str}
)
async def log_decision(args):
    """Persistiert Entscheidungen mit Timestamp."""
    log_path = Path("workspace/decisions.jsonl")
    log_path.parent.mkdir(exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "decision": args["decision"],
        "context": args.get("context", ""),
        "impact": args.get("impact", ""),
    }

    with open(log_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"content": [{"type": "text", "text": f"Entscheidung geloggt: {args['decision']}"}]}


@tool(
    "get_project_context",
    "Liest den aktuellen Projektkontext aus CLAUDE.md",
    {"section": str}
)
async def get_project_context(args):
    """Gibt Abschnitte aus CLAUDE.md zurück."""
    claude_md = Path("CLAUDE.md")
    if not claude_md.exists():
        return {"content": [{"type": "text", "text": "Kein CLAUDE.md gefunden"}]}

    content = claude_md.read_text()
    section = args.get("section", "")

    if section:
        lines = content.split("\n")
        in_section = False
        result = []
        for line in lines:
            if line.startswith(f"## {section}"):
                in_section = True
            elif line.startswith("## ") and in_section:
                break
            if in_section:
                result.append(line)
        content = "\n".join(result) if result else f"Abschnitt '{section}' nicht gefunden"

    return {"content": [{"type": "text", "text": content}]}


@tool(
    "summarize_audit_log",
    "Fasst die letzten N Einträge aus dem Audit-Log zusammen",
    {"n": int}
)
async def summarize_audit_log(args):
    """Zeigt die letzten Tool-Uses aus audit.log."""
    log_path = Path("workspace/audit.log")
    if not log_path.exists():
        return {"content": [{"type": "text", "text": "Kein Audit-Log vorhanden"}]}

    lines = log_path.read_text().strip().split("\n")
    n = args.get("n", 10)
    recent = lines[-n:] if len(lines) >= n else lines

    return {"content": [{"type": "text", "text": "\n".join(recent)}]}


# ─── MCP Server ───────────────────────────────────────────────────────────────

def create_project_server():
    """Erstellt einen MCP-Server mit allen custom Tools."""
    return create_sdk_mcp_server(
        "project-tools",
        tools=[log_decision, get_project_context, summarize_audit_log]
    )
