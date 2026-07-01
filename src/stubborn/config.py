"""Configuration and pruning budget defaults."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextBudget:
    """Token- and graph-aware limits for context pruning."""

    type_closure_depth: int | None = None
    call_closure_depth: int = 2
    max_symbols: int = 200
    max_tokens: int = 12_000
    exclude_patterns: tuple[str, ...] = field(
        default_factory=lambda: (
            "java/lang/",
            "java/util/",
            "java/io/",
        )
    )


DEFAULT_CONTEXT_BUDGET = ContextBudget()
