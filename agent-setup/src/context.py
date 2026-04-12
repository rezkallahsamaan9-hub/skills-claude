"""
AgentOS — Context Manager
===========================
Manages token budgets, compresses agent outputs, and controls
what gets loaded into each agent's context window.

Usage:
    from context import ContextBudget, compress_result

    budget = ContextBudget(max_tokens=4000)
    budget.add("explorer", explorer_result)
    budget.add("reviewer", reviewer_result)
    synthesis_prompt = budget.build_synthesis_prompt()
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ─── Token Estimation ────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English, ~3 for code."""
    return len(text) // 3


# ─── Result Compression ─────────────────────────────────────────────────────

def compress_result(text: str, max_words: int = 500) -> str:
    """
    Compress an agent result to fit within word budget.
    Keeps structure (headers, bullets) but truncates long paragraphs.
    """
    if not text:
        return ""

    words = text.split()
    if len(words) <= max_words:
        return text

    lines = text.split("\n")
    result_lines = []
    word_count = 0

    for line in lines:
        line_words = len(line.split())

        # Always keep headers and short lines
        if line.startswith("#") or line.startswith("-") or line.startswith("*") or line_words < 10:
            result_lines.append(line)
            word_count += line_words
        elif word_count + line_words <= max_words:
            result_lines.append(line)
            word_count += line_words
        else:
            # Truncate long paragraph
            remaining = max_words - word_count
            if remaining > 20:
                truncated = " ".join(line.split()[:remaining]) + "..."
                result_lines.append(truncated)
            break

        if word_count >= max_words:
            break

    return "\n".join(result_lines)


# ─── Context Budget ─────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    agent_name: str
    raw_tokens: int
    compressed_tokens: int
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ContextBudget:
    """
    Tracks token usage across agents and enforces budgets.
    Ensures the synthesis step gets compressed, relevant context.
    """
    max_tokens: int = 4000
    results: list[AgentResult] = field(default_factory=list)

    @property
    def used_tokens(self) -> int:
        return sum(r.compressed_tokens for r in self.results)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def add(self, agent_name: str, raw_result: str, max_words: int = 500) -> AgentResult:
        """Add an agent's result, compressing if needed."""
        raw_tokens = estimate_tokens(raw_result)

        # Adjust max_words based on remaining budget
        remaining_words = self.remaining_tokens // 2  # rough token-to-word ratio
        effective_max = min(max_words, remaining_words)

        compressed = compress_result(raw_result, max_words=max(50, effective_max))
        compressed_tokens = estimate_tokens(compressed)

        result = AgentResult(
            agent_name=agent_name,
            raw_tokens=raw_tokens,
            compressed_tokens=compressed_tokens,
            content=compressed,
        )
        self.results.append(result)
        return result

    def build_synthesis_prompt(self, task: str = "") -> str:
        """Build a prompt for the synthesis step with all compressed results."""
        sections = []
        for r in self.results:
            sections.append(f"## {r.agent_name}\n{r.content}")

        budget_note = f"[Budget: {self.used_tokens}/{self.max_tokens} tokens used]"

        return f"""Synthesize these agent results into a coherent response.
{budget_note}

Task: {task}

{'---'.join(sections)}

Rules:
- Combine findings, don't just concatenate
- Resolve contradictions
- Prioritize actionable items
- Max 600 words"""

    def summary(self) -> dict:
        """Return budget usage summary."""
        return {
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "remaining_tokens": self.remaining_tokens,
            "agents": [
                {
                    "name": r.agent_name,
                    "raw_tokens": r.raw_tokens,
                    "compressed_tokens": r.compressed_tokens,
                    "compression_ratio": f"{r.compressed_tokens/max(1,r.raw_tokens):.0%}",
                }
                for r in self.results
            ],
        }


# ─── Selective File Loading ──────────────────────────────────────────────────

def load_file_section(file_path: str, start_pattern: str = None, end_pattern: str = None) -> str:
    """
    Load only a section of a file matching patterns.
    Avoids loading entire large files into context.
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    lines = path.read_text().split("\n")

    if not start_pattern:
        return "\n".join(lines[:100])  # Default: first 100 lines

    capturing = False
    result = []
    for i, line in enumerate(lines):
        if start_pattern in line:
            capturing = True
        if capturing:
            result.append(f"{i+1}: {line}")
        if end_pattern and end_pattern in line and capturing:
            break

    return "\n".join(result) if result else f"Pattern '{start_pattern}' not found in {file_path}"


# ─── Project Context Snapshot ────────────────────────────────────────────────

def project_snapshot(cwd: str = ".") -> str:
    """
    Generate a minimal project context snapshot for agent injection.
    Much cheaper than reading all files.
    """
    root = Path(cwd)
    snapshot = []

    # Key files to check
    markers = {
        "package.json": "Node.js project",
        "requirements.txt": "Python project",
        "pyproject.toml": "Python project",
        "Cargo.toml": "Rust project",
        "go.mod": "Go project",
        "CLAUDE.md": "Claude Code project",
    }

    for filename, label in markers.items():
        if (root / filename).exists():
            snapshot.append(f"- {label} ({filename})")

    # Count files by extension
    extensions = {}
    for f in root.rglob("*"):
        if f.is_file() and not any(p in str(f) for p in [".git", "node_modules", ".venv", "__pycache__"]):
            ext = f.suffix or "(no ext)"
            extensions[ext] = extensions.get(ext, 0) + 1

    top_exts = sorted(extensions.items(), key=lambda x: -x[1])[:8]
    if top_exts:
        snapshot.append(f"- Files: {', '.join(f'{ext}({n})' for ext, n in top_exts)}")

    return "\n".join(snapshot) if snapshot else "Empty project"
