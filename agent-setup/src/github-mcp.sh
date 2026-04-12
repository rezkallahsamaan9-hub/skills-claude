#!/bin/bash
# GitHub MCP Server Wrapper
# Pulls token dynamically from gh CLI — nothing stored on disk.
export GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token)"
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
  echo "ERROR: gh auth token returned empty. Run: gh auth login" >&2
  exit 1
fi
exec npx -y @modelcontextprotocol/server-github "$@"
