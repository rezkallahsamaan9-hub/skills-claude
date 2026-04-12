#!/bin/bash
# n8n MCP Server Wrapper
# Pulls API key from macOS Keychain at runtime — nothing stored on disk.

N8N_KEY=$(security find-generic-password -s "n8n-api-key" -a "claude-agent" -w 2>/dev/null)

if [ -z "$N8N_KEY" ]; then
  echo "ERROR: n8n API key not found in Keychain." >&2
  echo "Store it with:" >&2
  echo "  security add-generic-password -s 'n8n-api-key' -a 'claude-agent' -w 'YOUR_KEY'" >&2
  exit 1
fi

export N8N_API_KEY="$N8N_KEY"
export N8N_BASE_URL="https://REMOVED_OLD_N8N_INSTANCE"

exec /Users/rezkallahsamaan/Desktop/skills-claude/agent-setup/.venv/bin/python3.12 \
  /Users/rezkallahsamaan/Desktop/skills-claude/agent-setup/src/mcp_n8n.py "$@"
