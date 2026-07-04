# ADR-013: Source-neutral workspace and contract endpoint queries

- **Status:** Accepted
- **Documented:** 2026-07-04
- **Deciders:** Stubborn maintainers

## Context

ADR-012 made contract evidence first-class in storage, but early query code still
treated code runs as the implicit workspace default. `latest_index_run_ids`
defaulted to `run_kind='code'`, and `prune_context` assumed every target stable
ID must resolve through `scip_symbol`.

That leaks the original Java-first path into the contract graph. A workspace that
contains only OpenAPI contract input has useful endpoint and schema facts, but no
code run. It should still be queryable.

This matters beyond a niche "contract-only" user. Frontend, TypeScript, mobile,
gateway, and integration teams often start from interface protocol facts rather
than backend implementation symbols. Which side of a distributed system has SCIP
coverage is a project detail, not a default the core graph should assume.

## Decision

Workspace queries are source-neutral by default. Code and contract sources are
peers distinguished by `index_run.run_kind`.

Call sites that need code symbols must explicitly request `run_kind='code'`.
Call sites that need contract facts must explicitly request `run_kind='contract'`.
Workspace summaries and source discovery should consider both source kinds.

`prune_context` accepts both code symbol stable IDs and contract endpoint stable
IDs as valid targets:

- A code target starts from `scip_symbol` and behaves as existing users expect.
- A contract endpoint target starts from `contract_endpoint` and can render
  endpoint/schema facts even when no code bindings exist.
- Contract traversal from endpoints to code symbols only happens through
  persisted `contract_binding` rows. OpenAPI endpoint identity must not invent
  provider/consumer code edges.

## Consequences

### Positive

- OpenAPI-only workspaces can be inspected and rendered.
- `stubborn info --workspace` can fulfill ADR-012's promise to distinguish code
  repos and contract sources.
- Frontend/interface-first users can ask about endpoint schemas without indexing
  backend source code.
- Existing Java/SCIP code paths remain deterministic because code-only readers
  still explicitly select `run_kind='code'`.

### Negative / trade-offs

- `PrunedGraph` needs a parallel contract endpoint structure in addition to code
  symbols and contract edges.
- Weavers and API responses must expose endpoint/schema facts without pretending
  they are Java declarations.
- Some reader helpers need more explicit source-kind parameters, which makes
  call sites slightly more verbose.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep `run_kind='code'` as the default everywhere | Hides contract-only workspaces and preserves an implementation-era bias. |
| Store contract endpoints as fake SCIP symbols | Reintroduces the ADR-012 problem: contract facts become indistinguishable from code facts. |
| Require every contract endpoint to bind to code before query | Blocks valid OpenAPI/schema use cases and encourages fake bindings. |
| Add a separate contract-only CLI disconnected from `context` | Splits the product model and prevents gradual composition with code symbols. |

## References

- [ADR-010](ADR-010-workspace-multi-repo-graph.md)
- [ADR-011](ADR-011-openapi-contract-graph.md)
- [ADR-012](ADR-012-schema-v4-contract-evidence.md)
- [CONTRACT-GRAPH.md](../CONTRACT-GRAPH.md)
