"""Lightweight token estimation (no external tokenizer dependency)."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Estimate token count using a chars/4 heuristic (adequate for budget caps)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
