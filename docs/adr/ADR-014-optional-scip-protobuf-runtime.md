# ADR-014: Optional SCIP protobuf runtime boundary

- **Status:** Accepted
- **Documented:** 2026-07-04
- **Deciders:** Stubborn maintainers

## Context

Stubborn started as a Java/SCIP-first tool, so the core package depended on the
Python `protobuf` runtime and imported generated SCIP bindings eagerly. That was
reasonable while every meaningful path started with `.scip` ingest.

ADR-011 through ADR-013 added contract sources as peers to code sources. A user
can now index and query OpenAPI endpoint/schema facts without a SCIP file. For
those users, importing `stubborn.api` or launching the CLI should not require the
SCIP protobuf runtime.

This is a packaging and import-boundary decision, not a change to SCIP's role.
SCIP remains the canonical machine index for code symbols.

## Decision

Move the Python `protobuf` runtime behind an optional `scip` extra and lazy-load
generated SCIP bindings only inside SCIP ingest paths.

Core install must support:

- database initialization and inspection,
- explicit contract manifest ingest,
- JSON OpenAPI contract ingest,
- contract endpoint browsing and source-neutral context queries,
- bundled JSON fixtures used for lightweight demos.

The `scip` extra is required for binary `.scip` and `.scip.ndjson` ingest. When a
user invokes those paths without `protobuf`, Stubborn should raise a clear
installation message instead of failing during unrelated imports.

Development installs include `protobuf` so the full test suite and binary SCIP
fixtures continue to run locally and in CI.

## Consequences

### Positive

- Contract-only and interface-first users can use the core package without SCIP
  runtime dependencies.
- CLI and API import paths match ADR-013's source-neutral model.
- SCIP ingest remains available through an explicit, discoverable extra.

### Negative / trade-offs

- Documentation must distinguish core install, OpenAPI YAML support, and SCIP
  binary/NDJSON support.
- Some tests need to verify import behavior in the absence of `protobuf`.
- JSON fixture ingest must avoid importing protobuf-heavy modules.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep `protobuf` as a core dependency | Preserves the original code-first packaging bias exposed by ADR-013. |
| Remove SCIP protobuf support from this package | Breaks the primary Java/SCIP workflow and contradicts ADR-001. |
| Make every SCIP-related module optional but leave eager CLI imports | Still breaks contract-only users at `import stubborn.cli`. |
| Split SCIP ingest into a separate distribution now | Larger migration with API compatibility costs; an extra is enough for the current boundary. |

## References

- [ADR-001](ADR-001-scip-as-machine-index.md)
- [ADR-007](ADR-007-java-first-beta-scope.md)
- [ADR-013](ADR-013-source-neutral-contract-queries.md)
