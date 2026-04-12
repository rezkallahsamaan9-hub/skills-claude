"""
Researcher Agent
-----------------
Web research agent, integrated with the orchestrator's tiering system.
Called by orchestrator.research() template or directly.
"""

from __future__ import annotations

import anyio
import sys

from claude_agent_sdk import (
    query, ClaudeAgentOptions, ResultMessage, AssistantMessage, TextBlock,
)


async def research(topic: str, model: str = "claude-sonnet-4-6", max_turns: int = 5) -> str:
    """Research a topic using WebSearch + WebFetch. Returns structured summary."""
    result = ""

    async for message in query(
        prompt=f"""Research: {topic}

1. Search for current, reliable sources (2025-2026)
2. Summarize the key findings
3. Give concrete recommendations or next steps
4. Be precise — max 300 words""",
        options=ClaudeAgentOptions(
            model=model,
            allowed_tools=["WebSearch", "WebFetch"],
            permission_mode="acceptEdits",
            max_turns=max_turns,
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text, end="", flush=True)
        elif isinstance(message, ResultMessage):
            result = message.result or ""

    return result


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "Claude Agent SDK best practices 2025"
    print(anyio.run(research, topic))
