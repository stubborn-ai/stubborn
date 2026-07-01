# ADR-001: SCIP as the machine index

- **Status:** Accepted
- **Documented:** 2026-07-02
- **Deciders:** Stubborn maintainers

## Context

LLMs need **structured, type-aware** context from large codebases. Building and maintaining a multi-language parser inside Stubborn would duplicate work already done by language communities and indexer teams.

We need a machine-readable index that:

- Provides **stable symbol IDs** across tools
- Supports **dependency and reference edges**
- Works with industry indexers (Java, and eventually C++, TypeScript, etc.)
- Stays **reproducible**: same index file → same graph

## Decision

Stubborn **does not parse source code**. It ingests [SCIP](https://github.com/sourcegraph/scip) indexes produced by external tools (primarily [scip-java](https://github.com/sourcegraph/scip-java) in beta).

Pipeline role:

```
Source → scip-java / scip-clang / … → index.scip → Stubborn ingest → SQLite → prune → weave
```

SCIP is the **machine index**. Stubborn is the **LLM-facing compiler** that turns that index into pruned stub text.

Supported ingest paths: binary `.scip`, `.scip.ndjson`, and JSON fixtures for tests. See [SCIP-INGEST.md](../SCIP-INGEST.md).

## Consequences

### Positive

- No parser maintenance burden in this repo
- Aligns with Sourcegraph / IDE ecosystem conventions
- Multi-language path is “add indexer + validate weave,” not “write a new front-end”
- `stubborn diff` operates on symbol sets — natural fit for SCIP snapshots

### Negative / trade-offs

- Users must run an indexer before Stubborn (extra step; mitigated by Docker E2E and docs)
- Edge quality depends on indexer output (we enrich with signature refs and occurrence links, but cannot invent symbols SCIP omitted)
- Beta weave quality is validated for Java; other languages need explicit E2E before we claim support

## Alternatives considered

| Option | Why not |
|--------|---------|
| **JavaParser / tree-sitter in-process** | High maintenance; fights existing SSOT tools; duplicates java-ast-ssot territory |
| **LSP-only** | No portable snapshot; hard to reconcile in CI |
| **Vector embeddings as primary index** | Non-deterministic; poor type fidelity; opposite of “stubborn” |
| **Raw file / directory walk** | No symbol graph; arbitrary chunk boundaries |

## References

- [SCIP-INGEST.md](../SCIP-INGEST.md)
- [proto/scip.proto](../../proto/scip.proto)
- [POSITIONING.md](../POSITIONING.md) — “Not a replacement for SCIP”
