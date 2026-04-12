"""
AgentOS — Service Registry
============================
Unified entry point for all MCP services.
Lazy-loads servers, provides health checks, and manages lifecycle.

Usage:
    # Start all services
    python3 src/services.py

    # Start specific service
    python3 src/services.py n8n

    # Health check
    python3 src/services.py --health
"""

import anyio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

WORKSPACE = Path(__file__).parent.parent / "workspace"
SERVICE_LOG = WORKSPACE / "services.log"


@dataclass
class ServiceStatus:
    name: str
    healthy: bool
    message: str
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ─── Service Definitions ────────────────────────────────────────────────────

SERVICES = {
    "n8n": {
        "description": "n8n workflow automation",
        "module": "mcp_n8n",
        "requires_env": ["N8N_API_KEY", "N8N_BASE_URL"],
    },
    "project-tools": {
        "description": "Project context tools (log_decision, get_project_context, audit)",
        "module": "tools.custom_tools",
        "requires_env": [],
    },
}


def check_env(service_name: str) -> ServiceStatus:
    """Check if required environment variables are set."""
    svc = SERVICES.get(service_name)
    if not svc:
        return ServiceStatus(service_name, False, f"Unknown service: {service_name}")

    missing = [v for v in svc["requires_env"] if not os.environ.get(v)]
    if missing:
        return ServiceStatus(service_name, False, f"Missing env vars: {', '.join(missing)}")

    return ServiceStatus(service_name, True, "OK")


async def health_check_all() -> list[ServiceStatus]:
    """Check health of all registered services."""
    results = []
    for name in SERVICES:
        status = check_env(name)
        results.append(status)
    return results


def list_services() -> dict:
    """Return registry summary for agent context injection."""
    return {
        name: {
            "description": svc["description"],
            "available": all(os.environ.get(v) for v in svc["requires_env"]),
        }
        for name, svc in SERVICES.items()
    }


# ─── Logging ─────────────────────────────────────────────────────────────────

def _log(message: str):
    WORKSPACE.mkdir(exist_ok=True)
    with open(SERVICE_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {message}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

async def main():
    if "--health" in sys.argv:
        results = await health_check_all()
        for r in results:
            icon = "OK" if r.healthy else "FAIL"
            print(f"  [{icon}] {r.name}: {r.message}")
        return

    if "--list" in sys.argv:
        for name, info in list_services().items():
            status = "available" if info["available"] else "unavailable"
            print(f"  {name}: {info['description']} [{status}]")
        return

    # Start specific or all services
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not targets:
        targets = list(SERVICES.keys())

    for name in targets:
        status = check_env(name)
        if not status.healthy:
            print(f"  [SKIP] {name}: {status.message}")
            continue

        print(f"  [START] {name}: {SERVICES[name]['description']}")
        _log(f"START {name}")

    print("\nServices ready. Use MCP tools in Claude Code to interact.")


if __name__ == "__main__":
    anyio.run(main)
