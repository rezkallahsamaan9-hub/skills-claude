"""
n8n MCP Server
---------------
Gibt Claude direkte Tools für n8n: Workflows lesen, bearbeiten, triggern.

Start:
    python3.12 src/mcp_n8n.py
"""

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from claude_agent_sdk import tool, create_sdk_mcp_server

# .env laden
load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.environ["N8N_API_KEY"]
BASE_URL = os.environ["N8N_BASE_URL"].rstrip("/")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}


def ok(text: str):
    return {"content": [{"type": "text", "text": text}]}


# ─── Tools ───────────────────────────────────────────────────────────────────

@tool("list_workflows", "Listet alle n8n Workflows mit ID, Name und Status", {})
async def list_workflows(args):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/v1/workflows?limit=100", headers=HEADERS)
        r.raise_for_status()
        workflows = r.json()["data"]

    lines = [f"{'🟢' if w['active'] else '⚫'} {w['name']}\n   ID: {w['id']}" for w in workflows]
    return ok(f"**{len(workflows)} Workflows:**\n\n" + "\n\n".join(lines))


@tool("get_workflow", "Liest einen Workflow vollständig (Nodes, Connections, Settings)", {"workflow_id": str})
async def get_workflow(args):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/v1/workflows/{args['workflow_id']}", headers=HEADERS)
        r.raise_for_status()
    return ok(json.dumps(r.json(), indent=2, ensure_ascii=False))


@tool("update_workflow", "Aktualisiert einen Workflow (Name, Nodes, Connections, Settings)", {"workflow_id": str, "workflow_json": str})
async def update_workflow(args):
    data = json.loads(args["workflow_json"])
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{BASE_URL}/api/v1/workflows/{args['workflow_id']}",
            headers=HEADERS,
            json=data,
            timeout=30,
        )
        r.raise_for_status()
    return ok(f"Workflow `{args['workflow_id']}` aktualisiert ✅")


@tool("activate_workflow", "Aktiviert oder deaktiviert einen Workflow", {"workflow_id": str, "active": bool})
async def activate_workflow(args):
    endpoint = "activate" if args["active"] else "deactivate"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/api/v1/workflows/{args['workflow_id']}/{endpoint}",
            headers=HEADERS,
        )
        r.raise_for_status()
    status = "aktiviert 🟢" if args["active"] else "deaktiviert ⚫"
    return ok(f"Workflow `{args['workflow_id']}` {status}")


@tool("trigger_workflow", "Triggert einen Workflow manuell mit optionalen Daten", {"workflow_id": str, "data": str})
async def trigger_workflow(args):
    payload = json.loads(args.get("data", "{}"))
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/api/v1/workflows/{args['workflow_id']}/run",
            headers=HEADERS,
            json={"data": payload},
            timeout=60,
        )
        r.raise_for_status()
    return ok(f"Workflow `{args['workflow_id']}` getriggert ✅\n{json.dumps(r.json(), indent=2)}")


@tool("get_executions", "Zeigt die letzten Ausführungen eines Workflows", {"workflow_id": str, "limit": int})
async def get_executions(args):
    limit = args.get("limit", 10)
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE_URL}/api/v1/executions?workflowId={args['workflow_id']}&limit={limit}",
            headers=HEADERS,
        )
        r.raise_for_status()
        execs = r.json().get("data", [])

    lines = [
        f"{'✅' if e['status'] == 'success' else '❌'} {e['startedAt']} | {e['status']} | ID: {e['id']}"
        for e in execs
    ]
    return ok(f"**Letzte {len(execs)} Ausführungen:**\n\n" + "\n".join(lines))


@tool("create_workflow", "Erstellt einen neuen leeren Workflow mit gegebenem Namen", {"name": str})
async def create_workflow(args):
    payload = {
        "name": args["name"],
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/api/v1/workflows", headers=HEADERS, json=payload)
        r.raise_for_status()
        wf = r.json()
    return ok(f"Workflow erstellt ✅\nName: {wf['name']}\nID: {wf['id']}")


# ─── Server starten ──────────────────────────────────────────────────────────

def get_n8n_server():
    """Returns MCP server config to pass to ClaudeAgentOptions(mcp_servers=...)."""
    return create_sdk_mcp_server("n8n", tools=[
        list_workflows, get_workflow, update_workflow,
        activate_workflow, trigger_workflow, get_executions, create_workflow
    ])


if __name__ == "__main__":
    print("n8n MCP Server config created.")
    print("Use: ClaudeAgentOptions(mcp_servers={'n8n': get_n8n_server()})")
    print(f"Tools: {', '.join(t.__class__.__name__ for t in [list_workflows, get_workflow, update_workflow, activate_workflow, trigger_workflow, get_executions, create_workflow])}")
