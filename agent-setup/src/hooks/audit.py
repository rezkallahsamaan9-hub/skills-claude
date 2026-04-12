"""
Audit Hooks
------------
PostToolUse-Hooks für Logging, Sicherheit und Monitoring.
"""

import json
from datetime import datetime
from pathlib import Path


AUDIT_LOG = Path("workspace/audit.log")


async def log_tool_use(input_data, tool_use_id, context):
    """Loggt jeden Tool-Use mit Timestamp."""
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    tool = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    # Sensitive Keys maskieren
    safe_input = {
        k: "***" if any(s in k.lower() for s in ["key", "token", "secret", "password"]) else v
        for k, v in tool_input.items()
    }

    with open(AUDIT_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {tool_use_id[:8]} | {tool} | {json.dumps(safe_input, ensure_ascii=False)}\n")

    return {}


async def warn_on_file_write(input_data, tool_use_id, context):
    """Warnt wenn in kritische Dateien geschrieben wird."""
    tool = input_data.get("tool_name", "")
    file_path = input_data.get("tool_input", {}).get("file_path", "")

    critical = [".env", "settings.json", "settings.local.json", "id_rsa", "credentials"]

    if any(c in file_path for c in critical):
        print(f"\n⚠️  Schreibe in kritische Datei: {file_path}\n")

    return {}
