# Positioning

## One-liner

**Stubborn** compiles symbol graphs into deterministic, privacy-safe LLM context.

## What it is

A **code context compiler**:

1. **Ingest** — SCIP symbol index → SQLite dependency graph
2. **Prune** — BFS from a target symbol with token/graph budgets
3. **Weave** — Emit declaration context (no method bodies)
4. **Reconcile** — Diff symbol sets for CI / migration guardrails

## Output formats

| Format | Since | Description |
|--------|-------|-------------|
| `java-stub` | v0.1 | Java-like declarations; best for codegen |
| `stubborn-dsl` | v0.7 | Compact type/edge graph; best for token savings |

Target-type **method signatures** in both formats since v0.9 (default `target`; use `--member-signatures neighbors|all` for more). See [STUBBORN-DSL.md](STUBBORN-DSL.md), [STUBBORN-DSL-GUIDE.md](STUBBORN-DSL-GUIDE.md).

## What it is not

- Not a vector database or embedding RAG
- Not a multi-language parser (use scip-java, scip-clang, etc.)
- Not an AST rewrite engine (that's OpenRewrite / java-ast-ssot)
- Not migration-only
- Not a replacement for SCIP (SCIP is the machine index; Stubborn is the LLM-facing compiler output)

## Ecosystem placement

```
stubborn-ai
└── stubborn           → LLM context compiler (any live repo)  ← this repo

anchor-migration (optional consumer)
├── db-metadata        → data layer SSOT
├── java-ast-ssot      → full Java AST SSOT (migration depth)
├── rewrite-recipes    → OpenRewrite migration recipes
└── migration-hub      → program docs (ADR-010 integration contract)
```

**Same philosophy** as db-metadata: SQLite snapshots, stable IDs, reconcile reports.  
**Different consumer**: LLMs and agents, not schema explorers.

## vs java-ast-ssot

| | java-ast-ssot | stubborn |
|---|---------------|-----------------|
| Question answered | "What's in this project?" | "What does the AI need right now?" |
| Parser | JavaParser | SCIP (industry standard) |
| Languages | Java | Java first; SCIP-multi-language path |
| Output | Full AST SQLite | Pruned stub **text** (`java-stub` or `stubborn-dsl`) |
| Token awareness | No | Core KPI |

They complement each other. Stubborn does not replace java-ast-ssot for migration crosswalk or Explorer.

## Privacy contract

**Included:** declarations, signatures, optional Javadoc (`--javadoc summary|full`)  
**Excluded:** method bodies, field initializers, annotation attribute values with business data

## Status

**Beta `0.9.0b3` (Java-first)** — see [BETA.md](BETA.md).
