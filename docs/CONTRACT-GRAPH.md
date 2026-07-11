# Contract Graph

Contract Graph is Stubborn's internal representation for distributed system
facts that are not code-symbol references. REST v1 ingest ships in-core as
`stubborn index-openapi` and `stubborn index-contract` ([ADR-011](adr/ADR-011-openapi-contract-graph.md),
[ADR-012](adr/ADR-012-schema-v4-contract-evidence.md)).

SCIP remains the canonical input for language symbols. Contract Graph facts come
from stable interface-protocol inputs such as OpenAPI YAML/JSON, explicit
manifests, generated clients, or future protocol adapters. They are composed
with SCIP symbols at workspace query time.

For REST v1, the stable input is the OpenAPI document. Code is used to validate
or bind that contract to implementation symbols; code is not the source of truth
for endpoint identity.

## Why It Exists

Programming languages have strict grammars, compilers, and versioned symbol
semantics. RESTful systems usually do not. Real systems mix path templates,
gateway rewrites, client libraries, generated code, hand-written WebClient
calls, implicit service discovery, version prefixes, and incomplete specs.

Contract Graph therefore uses **progressive formalization**:

1. Prefer authoritative contract specs when they exist.
2. Use code symbols to validate provider/consumer bindings to those specs.
3. Accept explicit human declarations when specs are incomplete.
4. Allow heuristic extraction only when clearly labeled as inferred and excluded
   from strict contract mode.
5. Preserve unknowns instead of forcing every relationship into a fake strong
   edge.

The goal is a deterministic and honest graph, not a universal REST theorem
prover.

## Sources

| Source | Status | Evidence floor |
|--------|--------|----------------|
| OpenAPI 3.x | Supported by `stubborn index-openapi` for endpoint/schema facts | `strong` for operations and schemas |
| Explicit binding manifest | Supported by `stubborn index-contract` | `declared` |
| Generated client/server code | Planned | `strong` when operation identity is traceable |
| Spring annotation / URL string extraction | Possible demo/lab adapter only | `inferred`; not a REST v1 authority source |
| AsyncAPI | Future | TBD |
| gRPC `.proto` | Future | TBD |
| Runtime traces/service mesh telemetry | Future | Observed, not source-of-truth |

## Minimal IR

The first durable IR should stay small.

```text
ContractEndpoint
  stable_id: string
  protocol: http | event | grpc | other
  service: string
  version: string | null
  operation: string | null
  method_or_verb: string | null
  address: string
  display_name: string | null

SchemaConstraint
  endpoint_stable_id: string
  location: path | query | header | requestBody | responseBody | message
  field_path: string
  type_name: string
  required: bool | null

ContractBinding
  endpoint_stable_id: string
  code_stable_id: string
  role: provider | consumer
  evidence: strong | declared | inferred | unknown
  source: string
```

Adapters may carry richer source-specific metadata, but prune/weave should only
depend on the common fields above.

## Stable IDs

Endpoint stable IDs should be derived from the authority source, not from a
consumer guess.

REST/OpenAPI first cut:

```text
openapi <service>:<version> <METHOD> <path-template>
```

Examples:

```text
openapi customers-service:v1 GET /owners/{ownerId}
openapi visits-service:v1 GET /pets/visits
```

Normalization should be conservative:

- Preserve path templates from the authority source.
- Normalize method case.
- Normalize obvious duplicate slashes.
- Do not silently equate unrelated prefixes such as `/api/customer/**` and
  `/owners/**` unless a gateway route or manifest declares the rewrite.
- Record version/source so drift can be diagnosed.

If no OpenAPI document or equivalent protocol contract exists, the REST adapter
should not fabricate strong endpoint identities from hand-written code. A
hand-written interface, annotation, or URL string may be useful as validation
evidence for an existing contract, but it is too ambiguous to be the stable input
for cross-repo unification.

## Evidence Tiers

| Tier | Meaning |
|------|---------|
| `strong` | Machine-generated or mechanically traceable binding, such as generated OpenAPI clients or server interfaces with operation identity. |
| `declared` | Human-authored manifest binding reviewed as part of the repo. |
| `inferred` | Heuristic match, such as URL string or annotation extraction. Useful, but not proof. |
| `unknown` | Endpoint or schema exists without a known code binding. |

Generated context must not hide these tiers. If a cross-service neighbor is
included only because of an `inferred` binding, output and MCP metadata should
make that visible.

Strict contract mode should exclude `inferred` bindings by default. Users can opt
into inferred bindings for exploratory runs, but those edges must not be
presented as deterministic proof of service communication.

## Schema v4 Status

Schema v4 makes contract evidence first-class:

- Persist endpoint/binding provenance and evidence tier.
- Keep contract edges distinguishable from SCIP code-reference edges.
- Compose code and contract graphs at query time.
- Expose evidence through structured API responses.
- Render contract sections in `stubborn-dsl` so generated context does not hide
  the evidence tier.

The current productized ingest entrypoints are:

```bash
stubborn index-contract --manifest contracts/http.json --out symbols.db
stubborn index-openapi --openapi openapi.yml --service customers-service --out symbols.db
```

`index-openapi` produces endpoint and schema facts from authoritative OpenAPI
YAML/JSON. It deliberately does not bind operations to code symbols by scanning
annotations, URL strings, or hand-written clients. Cross-service traversal still
requires `contract_binding` rows from an explicit manifest, generated client
traceability, or another evidence-producing adapter.

## Weave direction

`stubborn-dsl` output includes a `contracts:` block for endpoint facts, schema
constraints, and evidence-tiered bindings. Java stubs stay Java-shaped; contract
facts belong in `stubborn-dsl` or structured API fields, not fake Java declarations.

Example:

```text
contracts:
  http openapi customers-service:v1 GET /owners/{ownerId}
    provider declared OwnerResource
    consumer declared CustomersClient
    schema path.ownerId integer required
```

Playbook: [stubborn-hub CONTRACT-GRAPH-PLAYBOOK](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/CONTRACT-GRAPH-PLAYBOOK.md).

## Boundaries

- Contract Graph is not a replacement for OpenAPI, AsyncAPI, or protobuf.
- Core Stubborn should not parse Spring source to invent service topology.
- Heuristic extractors belong in adapters or demos and must emit evidence tiers.
- REST v1 requires an OpenAPI YAML/JSON document or equivalent stable protocol
  input. Without it, Stubborn should report "unsupported/no contract input" rather
  than silently normalize hand-written interfaces.
- Schema v4 stores first-class contract evidence; adapters should write
  contract tables instead of encoding service contracts as SCIP reference edges.

## References

- [ADR-001: SCIP as the machine index](adr/ADR-001-scip-as-machine-index.md)
- [ADR-010: Workspace graph for multi-repo source projects](adr/ADR-010-workspace-multi-repo-graph.md)
- [ADR-011: OpenAPI contract graph for distributed systems](adr/ADR-011-openapi-contract-graph.md)
- [ADR-012: Schema v4 contract evidence model](adr/ADR-012-schema-v4-contract-evidence.md)
