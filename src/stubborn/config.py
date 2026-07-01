"""Configuration and pruning budget defaults."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

PRUNE_MODES = frozenset({"smart", "strict", "fast"})


def normalize_prune_mode(mode: str) -> str:
    """Validate prune mode: smart (regex heuristics), strict (SCIP edges only), fast (smaller neighborhood)."""
    normalized = mode.strip().lower()
    if normalized not in PRUNE_MODES:
        allowed = ", ".join(sorted(PRUNE_MODES))
        raise ValueError(f"prune_mode must be one of: {allowed}")
    return normalized


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
    prune_mode: str = "smart"

    def __post_init__(self) -> None:
        object.__setattr__(self, "prune_mode", normalize_prune_mode(self.prune_mode))

    @property
    def use_signature_heuristics(self) -> bool:
        """Expand neighbors via signature regex (smart mode only)."""
        return self.prune_mode == "smart"


def apply_prune_mode(budget: ContextBudget) -> ContextBudget:
    """Apply mode-specific caps on top of explicit budget fields."""
    if budget.prune_mode != "fast":
        return budget

    type_depth = budget.type_closure_depth
    if type_depth is None:
        type_depth = 1
    else:
        type_depth = min(type_depth, 1)

    return replace(
        budget,
        type_closure_depth=type_depth,
        call_closure_depth=min(budget.call_closure_depth, 1),
        max_symbols=min(budget.max_symbols, 80),
    )


DEFAULT_CONTEXT_BUDGET = ContextBudget()
