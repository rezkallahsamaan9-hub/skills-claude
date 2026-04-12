#!/bin/bash
# Tavily MCP wrapper — loads API key from macOS Keychain at runtime
export TAVILY_API_KEY="$(security find-generic-password -s "tavily-api-key" -w 2>/dev/null)"

if [ -z "$TAVILY_API_KEY" ]; then
  echo "ERROR: tavily-api-key not found in Keychain" >&2
  exit 1
fi

exec npx -y tavily-mcp@latest
