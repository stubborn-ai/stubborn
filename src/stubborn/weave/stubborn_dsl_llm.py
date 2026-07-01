"""Short LLM-facing guide text for Stubborn-DSL context blocks."""

from __future__ import annotations

# Embedded in every stubborn-dsl weave output (# comments, ~30 tokens).
LLM_GUIDE_LINES: tuple[str, ...] = (
    "# Guide: pruned symbol graph — context only, not executable.",
    "# types: c=class i=interface e=enum r=record; @ = annotations.",
    "# edges: ref=uses type=type-use impl=implements def=defines; no bodies.",
)


def llm_guide_text() -> str:
    """Single string for system prompts or tool descriptions."""
    return (
        "stubborn-dsl blocks are pruned dependency graphs (declarations only). "
        "Types: c/i/e/r = class/interface/enum/record. "
        "Edges: ref, type, impl, def. "
        "Optional @ annotations. No method bodies."
    )
