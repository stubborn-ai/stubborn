# ADR-011: OpenAPI contract graph for distributed systems

- **Status:** Accepted
- **Documented:** 2026-07-04
- **Deciders:** Stubborn maintainers

## Context

ADR-001 made SCIP the machine index for code symbols. That boundary is still
correct: SCIP captures compile-time references between classes, methods, fields,
types, and other language symbols. It does not claim to model distributed system
interaction.

Microservice systems introduce a different class of facts:

- HTTP endpoints and path templates
- API gateway routes
- generated clients or hand-written WebClient/RestTemplate/Feign callers
- request/response DTO shapes
- service identity and versioning

Those relationships are often invisible to the compiler. A Java method calling
`http://customers-service/owners/{ownerId}` is not a static reference to
`OwnerResource#findOwner` in another service. The two services may live in
different repositories, languages, release trains, and build systems.

REST also differs from programming languages in how formal it is in practice.
Java, TypeScript, and similar languages have strict grammars, compilers, and
versioned symbol semantics. REST deployments often mix formal specs, gateway
rewrites, path conventions, generated clients, hand-written URL strings, and
incomplete documentation. Contract graph support must therefore use
**progressive formalization** rather than forcing every service interaction into
a fake strong edge.

Trying to make SCIP infer these REST relationships would blur Stubborn's design
line: Stubborn should not parse source in-process or invent semantic edges from
ad hoc string scans. But ignoring service contracts makes workspace graphs stop
at exactly the boundary that matters in real microservice refactors.

The ecosystem already reserved this direction as "SCIP canonical + opt-in
OpenAPI / LSP / DB adapters" and the `stubborn-ingest-*` naming pattern. The
PetClinic microservices demo uses a small hand-written HTTP contract bridge as a
seed validation, but the durable product boundary should be an OpenAPI-based
contract graph.

## Decision

Introduce a **contract graph** layer for distributed-system facts, starting with
OpenAPI for REST. SCIP remains the canonical machine index for code symbols.
OpenAPI YAML/JSON becomes the canonical machine index for REST contracts.

Define a small Stubborn Contract Graph IR for endpoint identity, payload schema
constraints, and producer/consumer bindings. OpenAPI is the first authority
source that maps into this IR; future AsyncAPI/gRPC adapters may map into the
same shape, but they are out of scope for the first implementation.

For REST v1, endpoint identity must come from the protocol contract, not from
implementation code. Code symbols validate or bind the contract to providers and
consumers; they do not define the canonical endpoint IDs.

The pipeline expands from code-only indexing:

```text
source -> SCIP -> code symbols -> symbols.db -> context
```

to workspace graph composition:

```text
workspace
  -> code repos -> SCIP -> code symbols
  -> service contracts -> OpenAPI -> endpoint symbols
  -> bindings/evidence -> cross-layer edges
  -> symbols.db -> context
```

The first adapter should be a separate optional package named
`stubborn-ingest-openapi`. It should ingest OpenAPI documents and produce
Stubborn-compatible graph facts without making the core repo an OpenAPI parser
or a Spring source analyzer.

If a project has no OpenAPI document or equivalent stable protocol contract, it
is out of scope for strong REST graph composition. A Spring annotation or
hand-written URL string extractor may exist later as an exploratory adapter, but
its output is `inferred` evidence and should be excluded from strict contract
mode by default.

Endpoint stable IDs must come from authoritative contract identity, not from
client source guesses. A first-cut scheme:

```text
openapi <service>:<version> <METHOD> <path-template>
```

Examples:

```text
openapi customers-service:v1 GET /owners/{ownerId}
openapi visits-service:v1 GET /pets/visits
```

The contract graph composes with code graphs at workspace query time, following
the same spirit as ADR-010: each input has its own latest run, and `context`
queries traverse the composed view. The OpenAPI adapter may initially emit a
Stubborn `IndexSnapshot` compatible with the current store. If contract facts
need richer provenance or schema-level fields later, a follow-up ADR should
define a schema version beyond v3.

The IR is documented in [CONTRACT-GRAPH.md](../CONTRACT-GRAPH.md). It is not a
replacement for OpenAPI or AsyncAPI; it is the compact graph shape Stubborn
needs for pruning and weaving.

### Evidence tiers

Every binding between a code symbol and a contract operation must carry an
honesty tier. This is as important as the edge itself because it controls what a
user can trust when Stubborn returns cross-service context.

| Tier | Meaning | Examples |
|------|---------|----------|
| `strong` | Machine-generated or mechanically traceable binding | OpenAPI generated server interface, generated client method, operationId-backed codegen |
| `declared` | Human-authored explicit binding in a manifest | `OrderClient#createOrder` declared to call `POST /orders` |
| `inferred` | Heuristic match that may be wrong | URL string/path-template match, annotation scan, gateway route pattern match |
| `unknown` | Contract exists, but no code binding is established | Endpoint symbol only |

`stubborn context` and future MCP responses should preserve this evidence in
metadata or output annotations before the feature is marketed as proof of live
service communication. A cross-service edge means "this fact was present at this
evidence tier," not necessarily "the production system definitely calls this
endpoint at runtime."

### Scope for the first version

Limit the first contract graph adapter to REST/OpenAPI:

- OpenAPI 3.x YAML/JSON documents as the stable input
- endpoint symbols
- request/response schema symbols where useful for stubs
- operationId/path/method stable IDs
- explicit or generated-client bindings

Do not include gRPC, AsyncAPI/message queues, service mesh telemetry, or runtime
traces in the first version. Those formats have different identity, versioning,
and evidence models.

## Consequences

### Positive

- Preserves ADR-001: SCIP remains the code symbol index; Stubborn still does not
  become a source parser.
- Gives microservice and REST refactors a deterministic, reviewable graph input
  instead of vector search or URL-string guesswork.
- Reuses ADR-010 workspace composition for multi-repo and multi-contract views.
- Opens a clean package boundary for `stubborn-ingest-openapi`.
- Makes honesty explicit through evidence tiers.

### Negative / trade-offs

- Adds a second machine-index family that users must manage alongside SCIP.
- Endpoint stable ID drift is a real risk: path templates, service versions, and
  operation IDs must be normalized carefully from the OpenAPI source.
- Binding code symbols to endpoints is the hard part. Strong evidence requires
  generated clients or operationId-backed traces; explicit manifests are
  `declared`; heuristic extraction must stay labeled as `inferred`.
- REST implementations are inconsistent. Normalization must be conservative and
  must expose drift rather than silently equating unrelated routes.
- Projects without a stable protocol contract cannot participate in strong REST
  graph composition. They can still use SCIP code context, but Stubborn should
  not pretend hand-written interfaces are canonical contract input.
- The v3 schema can host a prototype via compatible snapshots, but first-class
  evidence metadata may require a schema migration.
- Until that schema migration exists, v3-compatible contract bridge demos encode
  bindings as ordinary `reference` edges. That proves traversal shape but does
  not preserve evidence tier through `context` output.
- The story is REST-first, not "all microservice communication."

### Follow-up technical debt

ADR-012 defines the first implementation follow-up: schema v4 evidence metadata
and contract-aware output.

- persist `ContractEndpoint`, `SchemaConstraint`, and `ContractBinding`
  provenance/evidence
- distinguish contract bindings from SCIP `reference` edges at query time
- expose evidence tiers through `stubborn.api` and MCP
- render contract sections in `stubborn-dsl` or a sidecar output

Without this, the evidence-tier model remains documentation-only and users could
mistake a declared or inferred cross-service binding for a compiler-proven code
reference.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Teach SCIP to model REST | Exceeds SCIP's compile-time symbol mandate and would fork responsibility into language-specific plugins. |
| Parse Spring annotations and URL strings in core | Violates the no in-process parser/source-scanner boundary and creates weak edges without provenance. |
| Store `rest-call` directly as a new `scip_edge` kind | Mixes code-symbol and contract evidence without answering stable IDs or evidence tiers. |
| Use runtime traces only | Useful later, but non-deterministic, environment-dependent, and not available in CI/source-only validation. |
| Keep contract graph as demo-only YAML | Good as a seed validation, but too ad hoc for real users or adapter packages. |

## References

- [ADR-001](ADR-001-scip-as-machine-index.md)
- [ADR-003](ADR-003-type-neighbor-pruning.md)
- [ADR-010](ADR-010-workspace-multi-repo-graph.md)
- [SCIP-INGEST.md](../SCIP-INGEST.md)
- [CONTRACT-GRAPH.md](../CONTRACT-GRAPH.md)
- [ADR-012](ADR-012-schema-v4-contract-evidence.md)
- [POSITIONING.md](../POSITIONING.md)
- [stubborn-demo PetClinic microservices](https://github.com/stubborn-ai/stubborn-demo/tree/main/spring-petclinic-microservices)
