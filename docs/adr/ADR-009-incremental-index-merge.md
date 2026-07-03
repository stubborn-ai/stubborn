# ADR-009: Incremental index merge vs full snapshot

- **Status:** Accepted
- **Documented:** 2026-07-03
- **Deciders:** Stubborn maintainers

## Context

Today each `stubborn index` appends a **new `index_run`** with a full symbol graph ([ADR-002](ADR-002-sqlite-symbol-graph-ssot.md)). Downstream readers (`list_symbols`, `prune`, MCP `get_context`) default to the **latest** run. That model fits CI snapshots and `stubborn diff`, but not active development:

- A developer adds or edits a class and expects **agents to see it quickly** in `list_symbols` and neighborhood context — without re-ingesting the entire monorepo into a new run on every save.
- After **compile** (Maven/Gradle) or in **CI**, teams still need a **complete, auditable** index that matches the build — the current full-snapshot behavior.

[ADR-001](ADR-001-scip-as-machine-index.md) requires SCIP as the machine index: Stubborn must **not** parse Java (or other source) in-process to invent symbols. Incremental updates must therefore be **merge operations on SCIP-derived data**, orchestrated around external indexers (primarily scip-java in beta — [ADR-007](ADR-007-java-first-beta-scope.md)).

The ingest layer already walks SCIP `Document` messages with `relative_path`, but v1 schema does not persist path → symbol mapping, so we cannot replace or delete symbols for a single changed file inside an existing run.

## Decision

Introduce **two index write modes** on the same SQLite file (`symbols.db`):

| Mode | CLI (planned) | When to use | Effect on `index_run` |
|------|---------------|-------------|------------------------|
| **Full snapshot** | `stubborn index --scip … --out …` (default) | Post-compile, CI, release baselines | Append new `index_run` with complete graph (current behavior) |
| **Incremental merge** | `stubborn index --scip … --out … --merge` | Dev loop, file-save hooks, watch | Update **one active run** in place: replace symbols/edges for touched source paths only |

Both modes ingest from SCIP only. Merge does not relax the “no source parser” rule.

### Merge semantics

Given a SCIP index (full or filtered) and a target database:

1. **Resolve active run** — latest `index_run` in the DB, or create one if empty (same as today’s first `index`).
2. **Determine touched paths** — set `P` of `relative_path` values from SCIP `Document`s in this ingest (optionally restricted by `--paths` / `--changed-since` filters on the CLI).
3. **Delete** — remove all `scip_symbol` rows in the active run where `relative_path ∈ P`, and all `scip_edge` rows incident on those symbols.
4. **Insert** — write symbols and edges from the ingested snapshot for documents in `P` (same enrichment as full ingest: relationships, occurrences, `signature-ref`).
5. **Update provenance** — refresh `index_run.scip_hash`, `indexed_at`, and record merge metadata (`mode = 'merged'`, optional `parent_id` / `merge_count`).

Symbols whose `stable_id` changes after a rename appear as **delete-old-path + insert-new-path**; orphaned IDs from the old path are removed in step 3. Cross-file edges are only as complete as the SCIP indexer provides for the ingested documents — merge does not claim soundness beyond the SCIP input.

### Schema v2 (required)

v1 stores symbols without source path. v2 adds:

- `scip_symbol.relative_path TEXT` — document path from SCIP (nullable for `external_symbols`)
- Index on `(index_run_id, relative_path)` for efficient path-scoped delete
- `index_run.mode TEXT` — `'snapshot'` | `'merged'` (default `'snapshot'` for legacy runs)
- Optional lineage: `index_run.parent_id`, `merge_count`

`meta_schema_version` bumps to **2** with a migration script applied by `init_db` / writer on open.

### Orchestration (out of core merge, documented)

Stubborn **does not** run compilers. Fast dev UX is achieved by **orchestration** around merge:

| Layer | Responsibility |
|-------|------------------|
| **scip-java** (or other SCIP indexer) | Semantic analysis; produces `index.scip` |
| **stubborn `index --merge`** | Path-scoped graph update in SQLite |
| **`stubborn watch` (future)** | Debounced file watch → invoke indexer → `--merge` |
| **Build / CI** | `compile` → full SCIP index → `stubborn index` (snapshot, no `--merge`) |

MCP and CLI readers continue to use the same `STUBBORN_DB` file; no MCP protocol change is required for merge to take effect.

### Beta scope

- **Implement and E2E-validate merge for Java / scip-java first** ([ADR-007](ADR-007-java-first-beta-scope.md)).
- Other SCIP languages may use merge once ingest stores `relative_path`; weave E2E remains a separate gate for 1.0.

## Consequences

### Positive

- Developers and agents see new/changed types in `list_symbols` seconds after save, without growing unbounded `index_run` history during a session.
- Full snapshot mode preserves **audit trail** and `stubborn diff` workflows for CI ([ADR-002](ADR-002-sqlite-symbol-graph-ssot.md)).
- Aligns with ADR-001: SCIP remains authoritative; Stubborn adds **store semantics**, not a new parser.
- Same SQLite SSoT; MCP `get_context` benefits automatically after merge.

### Negative / trade-offs

- **Single-writer** assumption stricter during merge (concurrent merge + snapshot on one DB is undefined; document “one writer at a time”).
- Merge correctness depends on **indexer freshness** — if scip-java is stale, merge faithfully stores stale SCIP.
- **Partial document ingest** may miss cross-file edges until the next full snapshot or until dependent files are re-indexed.
- Schema migration (v1 → v2) must be tested; existing `symbols.db` artifacts need upgrade path.
- `stubborn watch` adds process supervision complexity (debounce, subprocess failures) — deferred to a follow-up CLI command, not required for merge MVP.

## Alternatives considered

| Option | Why not |
|--------|---------|
| **In-process Java AST / tree-sitter for “fast” updates** | Violates ADR-001; incomplete edges; duplicates ecosystem indexers |
| **Always append `index_run` on every save** | DB and `index_run` history grow quickly; `diff` noisy; does not match “one live view” dev expectation |
| **Re-read full SCIP and replace entire latest run** | Works without `relative_path`, but slow on large graphs and loses incremental provenance; rejected in favor of path-scoped delete |
| **Separate “dev.db” and “ci.db”** | Forces MCP/CLI to switch paths; merge into one active run is simpler |
| **LSP push notifications instead of SCIP** | No portable snapshot; poor fit for CI reconcile ([ADR-001](ADR-001-scip-as-machine-index.md)) |
| **Event stream / CRDT graph** | Over-engineered for beta; SQLite file remains the product artifact |

## Implementation notes (non-normative)

Suggested delivery order:

1. Schema v2 + ingest writes `relative_path` on document symbols
2. `IndexWriter.merge(snapshot, *, paths: set[str] | None)` + `--merge` CLI flag
3. demo-spring test: add document to fixture → merge → `list_symbols` sees new class
4. `stubborn watch` (Java globs, debounced scip-java + merge)
5. Document Maven/Gradle hook pattern for post-compile **full snapshot**

CLI filters (planned):

- `--merge` — enable merge mode
- `--paths path1,path2` — limit `P` (paths must match SCIP `relative_path`)
- `--changed-since <iso>` — optional; filter documents by SCIP/metadata timestamps when available

## References

- [ADR-001: SCIP as the machine index](ADR-001-scip-as-machine-index.md)
- [ADR-002: SQLite symbol graph as SSoT](ADR-002-sqlite-symbol-graph-ssot.md)
- [ADR-007: Java-first beta scope](ADR-007-java-first-beta-scope.md)
- [SCIP-INGEST.md](../SCIP-INGEST.md)
- [src/stubborn/store/schema/v1.sql](../../src/stubborn/store/schema/v1.sql)
- [src/stubborn/store/writer.py](../../src/stubborn/store/writer.py)
- [src/stubborn/ingest/extract.py](../../src/stubborn/ingest/extract.py)
