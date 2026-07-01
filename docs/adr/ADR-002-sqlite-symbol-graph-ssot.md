# ADR-002: SQLite symbol graph as SSoT

- **Status:** Accepted
- **Date:** 2026-03-01 (retroactive; formalized 2026-07-02)
- **Deciders:** Stubborn maintainers

## Context

After SCIP ingest, Stubborn needs a **durable, queryable** representation of symbols and edges for:

- Pruning from a target symbol
- `list_symbols` / MCP discovery
- `info` and metrics (compression KPIs)
- `diff` / reconcile between two indexing runs

The store must be easy to ship (single file), inspect (CLI + SQL), and embed in CI artifacts.

## Decision

Persist each ingest as a **SQLite database** (typically `symbols.db`) with schema **v1** defined in [`src/stubborn/store/schema/v1.sql`](../../src/stubborn/store/schema/v1.sql).

Core tables:

- `index_run` — provenance (SCIP source, language, tool version)
- `scip_symbol` — stable_id, display_name, kind, signature, documentation
- `scip_edge` — typed relationships between symbols

SQLite is the **single source of truth** for all downstream operations. We do not keep a parallel in-memory graph format as the canonical store.

## Consequences

### Positive

- One file per index — simple artifact upload in CI (`symbols.db`)
- Familiar ops: copy, diff symbol sets, attach in debugging
- Same snapshot philosophy as sibling tools (e.g. db-metadata) without coupling to them
- Schema versioning via `meta_schema_version` allows controlled migrations later

### Negative / trade-offs

- Single-writer semantics; no concurrent index writes (acceptable for CLI/agent use)
- Very large monorepo indexes may need tuning (indexes on `stable_id` already in v1)
- Graph algorithms run in Python over SQL rows, not inside the database engine

## Alternatives considered

| Option | Why not |
|--------|---------|
| **In-memory only** | No CI artifact handoff; agents cannot reuse index across sessions without re-ingest |
| **Neo4j / dedicated graph DB** | Operational overhead; poor fit for “drop a file in the repo” workflows |
| **Re-read SCIP on every `context` call** | Slow; SCIP files can be large; loses stable reconcile surface |
| **JSON / NDJSON export as SSoT** | Weaker querying; harder to enforce referential integrity for edges |

## References

- [src/stubborn/store/schema/v1.sql](../../src/stubborn/store/schema/v1.sql)
- [src/stubborn/store/writer.py](../../src/stubborn/store/writer.py)
- [src/stubborn/store/reader.py](../../src/stubborn/store/reader.py)
