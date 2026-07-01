# ADR-003: Type-neighbor BFS pruning with token budget

- **Status:** Accepted
- **Date:** 2026-05-01 (retroactive; formalized 2026-07-02)
- **Deciders:** Stubborn maintainers

## Context

A full SCIP index for a real project can describe hundreds or thousands of symbols. LLM context windows are finite and expensive. Dumping whole files or unconstrained symbol subsets causes:

- Token waste (80–90% of source is irrelevant to one task)
- Type hallucinations when the model lacks the right neighbor declarations
- Privacy risk when method bodies leak business logic

We need **deterministic**, **target-scoped** context: given `OrderService#`, include the types and signatures the symbol graph proves are relevant — nothing guessed from embeddings.

## Decision

Implement pruning as **breadth-first expansion** from a target `stable_id` over the SQLite edge graph, governed by `ContextBudget` ([`src/stubborn/config.py`](../../src/stubborn/config.py)):

| Knob | Default | Role |
|------|---------|------|
| `call_closure_depth` | 2 | How far to follow call/reference edges |
| `max_symbols` | 200 | Hard cap on symbol count |
| `max_tokens` | 12_000 | Estimated token ceiling (chars/4 heuristic) |
| `exclude_patterns` | JDK packages | Skip `java/lang/`, `java/util/`, … noise |

Algorithm highlights ([`src/stubborn/graph/prune.py`](../../src/stubborn/graph/prune.py)):

- BFS from target with depth limits per edge kind
- Type-neighbor expansion via signature parsing and occurrence links
- Type members (methods/fields) attached when pruning a type symbol
- Output: `PrunedGraph` → weavers; if over budget, symbols dropped and `dropped_for_budget` flagged

**Same prune step** feeds both `java-stub` and `stubborn-dsl` (ADR-005).

## Consequences

### Positive

- Reproducible: same DB + target + budget → same pruned graph
- KPI-friendly: `metrics` compares stub vs full source tree
- Tunable for agents via API/MCP parameters
- CI guard scripts assert expected **type neighbors** in demo-spring cases

### Negative / trade-offs

- Signature type inference uses regex heuristics — can miss qualified names or generics edge cases
- JDK excludes are string patterns, not semantic module awareness
- Token estimate is `chars/4`, not model-specific (documented in [BETA.md](../BETA.md))
- Not a substitute for human judgment on very deep call chains (depth defaults are conservative)

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Vector RAG / semantic search** | Non-deterministic; chunks ignore type graph; drift on re-embed |
| **Full file inclusion** | Token cost; privacy; unrelated code noise |
| **Fixed package-level scope** | Too coarse for method-level tasks; too fine for cross-module flows |
| **LLM asks for files iteratively** | Slow; expensive; no reproducible CI baseline |

## References

- [src/stubborn/graph/prune.py](../../src/stubborn/graph/prune.py)
- [src/stubborn/config.py](../../src/stubborn/config.py)
- [examples/demo-spring/cases/](../../examples/demo-spring/cases/) — expected neighbor catalogs
- [BETA.md](../BETA.md) — KPI baselines
