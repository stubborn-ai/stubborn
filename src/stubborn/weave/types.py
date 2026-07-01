"""Shared weave result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeaveResult:
    text: str
    symbol_count: int
    estimated_tokens: int
    dropped_for_budget: int = 0
