# ADR-012: Schema v4 contract evidence model

- **Status:** Accepted
- **Documented:** 2026-07-04
- **Deciders:** Stubborn maintainers

## Context

ADR-011 defines the Contract Graph direction: OpenAPI is the authority source for
REST contract facts, and bindings between code symbols and contract endpoints
carry evidence tiers (`strong`, `declared`, `inferred`, `unknown`).

The schema v3 PetClinic microservices demo proves traversal shape by encoding
declared HTTP contract bindings as ordinary snapshot symbols and `reference`
edges. That is useful as a seed validation, but it creates a real product gap:
once contract bindings reach `stubborn context`, they are indistinguishable from
compiler-proven SCIP references.

That violates the honesty requirement in CONTRACT-GRAPH.md: generated context
must not hide evidence tiers.

## Decision

Define schema v4 as the first-class contract evidence schema.

### Storage separation

Code-symbol facts and contract facts must be physically separate in storage:

- `scip_symbol` and `scip_edge` remain code graph tables.
- Contract endpoints, schema constraints, and code-to-contract bindings live in
  dedicated contract tables.
- Query code may compose these graphs, but write paths must not encode contract
  bindings as `scip_edge.reference`.

This makes it impossible for a contract edge to be mistaken for a compiler
reference merely because a writer forgot to attach metadata.

### Source tracking

Reuse `repo` and `index_run` for versioning and workspace latest views. A
contract source is a workspace source, not necessarily a code repository.

Add `index_run.run_kind`:

```sql
ALTER TABLE index_run ADD COLUMN run_kind TEXT NOT NULL DEFAULT 'code'
    CHECK (run_kind IN ('code', 'contract'));
```

Existing databases remain code-only because the default is `code`.

`stubborn info --workspace` should distinguish code repos from contract sources
instead of reporting a misleading single repo count:

```text
Code repos:        4
Contract sources: 1
```

The first implementation may still store an OpenAPI source under a normal
`repo.repo_key` such as `petclinic-contracts`; UI and summary output must label
it by `run_kind`.

### Tables

```sql
CREATE TABLE IF NOT EXISTS contract_endpoint (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    stable_id       TEXT NOT NULL,
    protocol        TEXT NOT NULL,
    service         TEXT,
    version         TEXT,
    method_or_verb  TEXT,
    address         TEXT NOT NULL,
    display_name    TEXT,
    UNIQUE (index_run_id, stable_id)
);

CREATE TABLE IF NOT EXISTS contract_schema_constraint (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id         INTEGER NOT NULL REFERENCES contract_endpoint(id),
    location            TEXT NOT NULL CHECK (
        location IN ('path','query','header','requestBody','responseBody','message')
    ),
    field_path          TEXT NOT NULL,
    type_name           TEXT,
    required            INTEGER
);

CREATE TABLE IF NOT EXISTS contract_binding (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id         INTEGER NOT NULL REFERENCES contract_endpoint(id),
    code_stable_id      TEXT NOT NULL,
    role                TEXT NOT NULL CHECK (role IN ('provider','consumer')),
    evidence            TEXT NOT NULL CHECK (
        evidence IN ('strong','declared','inferred','unknown')
    ),
    source              TEXT,
    UNIQUE (endpoint_id, code_stable_id, role)
);

CREATE INDEX IF NOT EXISTS idx_contract_binding_code
    ON contract_binding (code_stable_id);

CREATE INDEX IF NOT EXISTS idx_contract_binding_endpoint
    ON contract_binding (endpoint_id);
```

`contract_binding.code_stable_id` intentionally does not foreign-key to
`scip_symbol.id`. Bindings must follow stable IDs across repo re-indexes and
workspace latest-run selection. Query-time resolution maps `code_stable_id` to
the current canonical symbol row, matching ADR-010.

Endpoint stable IDs must remain in a namespace that cannot collide with SCIP
symbols, for example:

```text
openapi customers-service:v1 GET /owners/{ownerId}
```

Writers should enforce this namespace for OpenAPI endpoints rather than relying
on convention.

### Write behavior

Writers must not use broad `INSERT OR IGNORE` for contract data. Constraint
failures such as invalid `evidence` values must surface as errors.

When deduping legitimate duplicate bindings, use explicit conflict targets:

```sql
ON CONFLICT(endpoint_id, code_stable_id, role) DO NOTHING
```

This preserves the lesson from earlier edge-kind constraint bugs: schema checks
are part of the correctness contract, not noise to suppress.

### Query and pruning

`prune_context` should keep existing behavior for databases without contract
data.

When contract data exists:

1. BFS from code symbols uses normal SCIP adjacency as today.
2. When visiting a code stable ID, look up contract bindings by
   `contract_binding.code_stable_id`.
3. Traverse from code symbol to endpoint, then from endpoint to other bindings'
   code symbols.
4. Resolve those code stable IDs against the latest selected workspace runs,
   not against historical `scip_symbol.id` values.
5. Preserve role and evidence on the contract traversal edge.

`--prune-mode strict` should exclude `inferred` bindings by default and include
only `strong` and `declared` contract bindings. `smart` may include `inferred`
bindings, but they must remain labeled as inferred.

### Pruned graph shape

Do not overload `PrunedGraph.edges: list[tuple[str, str, str]]` with optional
fourth fields. Add a parallel structure:

```python
@dataclass(frozen=True)
class ContractPrunedEdge:
    endpoint_stable_id: str
    code_stable_id: str
    role: Literal["provider", "consumer"]
    evidence: Literal["strong", "declared", "inferred", "unknown"]
    source: str | None

@dataclass
class PrunedGraph:
    target_stable_id: str
    symbols: list[PrunedSymbol]
    edges: list[tuple[str, str, str]]
    contract_edges: list[ContractPrunedEdge]
```

This keeps code edges and contract evidence structurally separate for all
downstream consumers.

### Weave and API output

`java-stub` should remain Java-shaped and should not embed contract blocks.

`stubborn-dsl` should add a separate `contracts:` section, for example:

```text
contracts:
  http openapi customers-service:v1 GET /owners/{ownerId}
    provider strong OwnerResource
    consumer declared CustomersServiceClient
```

`stubborn.api` and MCP responses must expose structured contract evidence, not
only rendered text. A first-cut API field can be a summary such as:

```python
contract_evidence_summary: list[dict[str, str]]
```

Agents that consume JSON instead of rendered text must still see evidence tiers.

## Consequences

### Positive

- Contract facts and SCIP facts cannot be confused at the storage layer.
- Existing code-only databases and users keep current behavior.
- Evidence tiers become queryable and renderable instead of documentation-only.
- `strict` mode gains a natural contract interpretation without inventing a new
  user-facing mode.
- Contract sources reuse workspace/latest-run machinery from ADR-010.

### Negative / trade-offs

- Schema v4 introduces more tables and reader/writer complexity.
- `stubborn info --workspace` must learn to summarize source kinds.
- Prune/weave/API models need explicit contract-edge handling.
- PetClinic microservices demo must be migrated from synthetic `reference` edges
  to real contract tables.
- Backwards-compatible migration is easy, but test coverage must include
  negative constraint checks.

## Migration and test requirements

Add `migrate_v3_to_v4.sql` and `schema/v4.sql`.

Migration must be additive:

- add `index_run.run_kind` with default `code`
- add contract tables
- add contract indexes
- update `meta_schema_version` to 4

Required tests:

- Fresh schema init creates v4 tables and `run_kind`.
- v3 databases migrate to v4 without changing code graph behavior.
- Invalid `evidence` values fail CHECK constraints.
- Writers do not hide CHECK failures with broad `INSERT OR IGNORE`.
- `strict` pruning excludes `inferred` contract bindings.
- `smart` pruning includes `inferred` bindings while preserving evidence.
- `stubborn-dsl` renders contract sections with role and evidence.
- API/MCP results include structured contract evidence.
- PetClinic microservices uses `evidence='declared'` bindings and can remove
  its v3 limitation disclaimer only after this migration is live.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep v3 synthetic `reference` edges | Proven useful for seed validation, but hides evidence tiers and confuses contract facts with SCIP facts. |
| Add `evidence` to `scip_edge` | Pollutes the code graph table and still permits contract/code fact confusion. |
| Foreign-key `contract_binding.code_stable_id` to `scip_symbol.id` | Binds to one historical run and breaks ADR-010 latest-run composition. |
| Create a separate source table instead of reusing `repo`/`index_run` | Cleaner naming, but duplicates workspace/latest-run mechanics before we know the contract source model needs it. |
| Add a new user-facing prune mode for contracts | Unnecessary first cut; extend existing `strict`/`smart` semantics with evidence filtering. |

## References

- [ADR-010](ADR-010-workspace-multi-repo-graph.md)
- [ADR-011](ADR-011-openapi-contract-graph.md)
- [CONTRACT-GRAPH.md](../CONTRACT-GRAPH.md)
- [src/stubborn/store/schema/v3.sql](../../src/stubborn/store/schema/v3.sql)
