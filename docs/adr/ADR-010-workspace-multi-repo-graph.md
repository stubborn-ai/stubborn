# ADR-010: Workspace graph for multi-repo source projects

- **Status:** Accepted
- **Documented:** 2026-07-04
- **Deciders:** Stubborn maintainers

## Context

Medium and large Java systems are often split across multiple repositories, Maven
modules, or deployable JARs. A single `symbols.db` previously exposed only the
latest global `index_run`, so indexing Repo B after Repo A made Repo A invisible
to `list_symbols` and `context`. That model is clean for one repo, but it cannot
represent an internal workspace where Repo A calls source-defined symbols in
Repo B.

There are two different problems:

1. **Graph composition** for source-available internal repos.
2. **Freshness** for local edits without forcing every repo to recompile or
   re-index.

External JAR-only dependencies are a separate constraint. SCIP can expose
signatures for dependencies seen by the compiler, but Stubborn cannot invent a
deep source graph for a JAR when the source has not been indexed.

## Decision

Add a workspace graph model. A workspace contains repos, each repo has its own
latest `index_run`, and a workspace query selects the latest run for every repo
in that workspace. `prune_context` can then resolve a `stable_id` across the
selected latest runs and continue traversal in the repo that owns the preferred
source-defined symbol.

Run-local edges remain run-local. We do not create synthetic cross-run edge rows
in the store. Cross-repo continuation is resolved at query time by stable ID:
when Repo A has an edge to a symbol that Repo B also defines, the query resolver
prefers Repo B's source-defined symbol over Repo A's external/signature-only
symbol.

External JAR-only dependencies remain leaves unless their source is indexed as a
repo in the same workspace.

## Consequences

### Positive

- Internal multi-repo workspaces can be queried as one coherent latest graph.
- Each repo can be indexed and merged independently, preserving the fast
  `stubborn-watch` path.
- Existing single-repo users keep the old default: latest global run.
- Query-time composition avoids rewriting stored edges during every repo update.

### Negative / trade-offs

- Workspace queries need deterministic tie-breaking when the same `stable_id`
  appears in multiple repos.
- `diff` and release baselines must be explicit about whether they compare a
  single run or a workspace view.
- JAR-only dependencies cannot provide live deep context without source indexes.
- One local SQLite file is still the first-cut concurrency boundary; multiple
  writers should serialize writes.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep one latest global run | Makes multiple indexed repos overwrite the visible graph. |
| Merge all repos into one synthetic run | Requires rewriting unrelated repo symbols on every repo update. |
| Store synthetic cross-run edges | More write complexity and harder invalidation; stable ID resolution is enough for first cut. |
| Promise live JAR dependency graphs | Not supported by SCIP input when only compiled artifacts are available. |

## References

- [ADR-009](ADR-009-incremental-index-merge.md)
- [src/stubborn/graph/prune.py](../../src/stubborn/graph/prune.py)
- [src/stubborn/store/reader.py](../../src/stubborn/store/reader.py)
- [stubborn-watch](https://github.com/stubborn-ai/stubborn-watch)
