# Positioning

## One-liner

**Stubborn** is an **LLM context compiler for SCIP-indexed codebases** — Java/Spring first — that turns symbol graphs into deterministic, privacy-safe stub text with measurable token savings.

It is **not** a zero-configuration repo map. You (or your CI) run a SCIP indexer first; Stubborn compiles the index into pruned context for agents and audit pipelines.

## Who it is for

### Primary — teams with a SCIP workflow (Java / Spring)

- Large **Java / Spring** estates, legacy modernization, refactor programs
- Need **reproducible** context: same index + target → same stub (CI baselines, KPI guards)
- Need **audit-friendly** artifacts: `diff`, reconcile, SQLite snapshot history
- Often overlap with structured migration runbooks (optional [anchor-migration](INTEGRATION.md) consumer)

**Success looks like:** indexed repo → `stubborn context` / MCP → bounded stub text → LLM or PR gate, with compression metrics you can defend.

### Secondary — individual agent users (Cursor / MCP)

- Already have or can produce **`symbols.db`** (Docker E2E, fixture, or scip-java in CI)
- Want **deterministic** `get_context` instead of ad-hoc file gathering
- Accept **setup friction** in exchange for type-neighbor pruning and token KPIs

**Success looks like:** MCP tools return pruned stubs before codegen — not “open repo and go” like [Aider repo-map](https://aider.chat/docs/repomap.html).

Stubborn serves both, but **features and CI investment skew Primary** (reconcile, validation cases, demo runbooks). Secondary users should start with the [30-second fixture path](../README.md#try-in-30-seconds-no-java-required) or [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo).

## What it is

A **code context compiler**:

1. **Ingest** — SCIP symbol index → SQLite dependency graph
2. **Prune** — BFS from a target symbol with token/graph budgets ([`--prune-mode`](adr/ADR-003-type-neighbor-pruning.md))
3. **Weave** — Emit declaration context (`java-stub` or `stubborn-dsl`) — **user choice**
4. **Reconcile** — Diff symbol sets for CI / migration guardrails (Primary audience)

## What it is not

| Claim | Reality |
|-------|---------|
| “Drop-in replacement for vector RAG” | One approach among several; many tools mix symbols + embeddings |
| “Zero-config like repo-map” | Requires **SCIP index** (e.g. scip-java) before Stubborn runs |
| “Any language, production-ready today” | **Java-first beta**; other SCIP languages may ingest experimentally — weave not validated |
| “We never guess” | **`smart`** mode uses signature heuristics; use **`strict`** for SCIP-only neighbors ([ADR-003](adr/ADR-003-type-neighbor-pruning.md)) |
| Multi-language parser | Use scip-java, scip-clang, etc. — Stubborn consumes indexes |
| AST rewrite / migration engine | See OpenRewrite, java-ast-ssot |
| Replacement for SCIP | SCIP is the code-symbol machine index; Stubborn is the LLM-facing compiler output |
| Automatic microservice topology discovery | Planned contract graph support starts from authoritative OpenAPI facts, not runtime guesses or URL-string scraping |

## How we compare (honest axes)

Evaluate tools on three axes — not a single “RAG vs symbols” slide:

| Axis | Stubborn | Typical vector chunk RAG | IDE symbol tools (e.g. repo-map, Cody) |
|------|----------|--------------------------|----------------------------------------|
| **Determinism** | Same SCIP + target + options → same output | Embedding / chunk drift | Varies; often IDE-integrated |
| **Type structure** | Symbol graph + declared signatures | Text chunks | Symbols / AST / hybrid |
| **Setup friction** | **High** — SCIP index required | Medium | **Low** — open repository |

Stubborn wins when **determinism + token KPI + privacy contract** matter more than **lowest time-to-first-query**. It loses on friction vs tools that index from a git checkout alone.

## Setup path (be explicit)

| Path | Prerequisites | Best for |
|------|---------------|----------|
| **Fixture** (30s) | `pip install stubborn-stub` | Try the compiler; no Java |
| **Agents (MCP)** | `pip install stubborn-stub stubborn-mcp` | Cursor with `symbols.db` — see [stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp) |
| **Docker E2E** | Docker Desktop + `stubborn-demo` | Reproduce demo-spring and scale-up validation |
| **Real Java project** | JDK, Maven/Gradle, **scip-java**, Python | Primary production use |

Real workflow:

```text
source → scip-java index → index.scip → stubborn index → symbols.db → stubborn context
```

There is no supported path that skips SCIP for live code.

Planned distributed-system workflow ([ADR-011](adr/ADR-011-openapi-contract-graph.md)):

```text
source → SCIP → code symbols
OpenAPI → endpoint symbols
bindings/evidence → workspace graph → stubborn context
```

SCIP remains the canonical index for code symbols. OpenAPI is the planned
canonical index for REST contract facts; it complements SCIP rather than
replacing it.

## Language scope

| Layer | Beta status |
|-------|-------------|
| SCIP **ingest** | Multi-format (`.scip`, ndjson, fixtures) — language-agnostic |
| **Weave** / E2E / KPI | **Java / Spring validated only** ([BETA.md](BETA.md)) |
| **Prune defaults** | JDK exclude patterns assume Java |

Non-Java SCIP indexes may work experimentally; we do **not** claim production weave quality until language-specific E2E exists ([ADR-007](adr/ADR-007-java-first-beta-scope.md)).

## Output formats (user choice)

| Format | When |
|--------|------|
| **`java-stub`** (default) | Pure Java / Spring — codegen and in-place edit |
| **`stubborn-dsl`** | Mixed-language repos, token-sensitive tasks, graph-first audit ([ADR-005](adr/ADR-005-dual-output-formats.md)) |

Both share the same prune step. DSL is retained for **polyglot / cross-language context** long-term, not because it beats `java-stub` on every Java-only task.

## Neighbor expansion (user choice)

| `--prune-mode` | When |
|----------------|------|
| **`smart`** (default) | Richest neighbors; CI guards assume this |
| **`strict`** | Audits requiring SCIP-proven edges only |
| **`fast`** | Tight token budget; smaller neighborhood |

See [ADR-003](adr/ADR-003-type-neighbor-pruning.md) for honesty tiers (SCIP edges vs `signature-ref` vs prune-time regex).

## Contract graph direction

Microservice and REST relationships are not compile-time symbol references. The
planned contract graph layer uses authoritative OpenAPI documents for endpoint
identity and explicit evidence tiers for code-to-endpoint bindings
([CONTRACT-GRAPH.md](CONTRACT-GRAPH.md), [ADR-011](adr/ADR-011-openapi-contract-graph.md)):

- `strong`: generated client/server or operationId-backed binding
- `declared`: human-authored manifest binding
- `inferred`: heuristic URL/path/template match
- `unknown`: endpoint exists without a proven code binding

This keeps Stubborn's determinism and honesty contract intact while letting
workspace context cross service boundaries when the relevant contract facts are
available.

For REST, the stable input is the OpenAPI YAML/JSON document. Code symbols are
used to validate or bind providers and consumers to that contract. If a project
has only hand-written interfaces, annotations, or URL strings, Stubborn should
not treat them as strong REST graph input.

## Ecosystem placement

```
stubborn-ai
├── stubborn           → LLM context compiler (SCIP-indexed repos)
└── stubborn-mcp       → MCP server for agents (PyPI)

anchor-migration (optional consumer)
├── db-metadata        → data layer SSOT
├── java-ast-ssot      → full Java AST SSOT (migration depth)
├── rewrite-recipes    → OpenRewrite migration recipes
└── migration-hub      → program docs (ADR-010 integration contract)
```

**Same philosophy** as db-metadata: SQLite snapshots, stable IDs, reconcile reports.  
**Different consumer**: LLMs and agents, not schema explorers.

Key design decisions: [adr/README.md](adr/README.md).

## vs java-ast-ssot

| | java-ast-ssot | stubborn |
|---|---------------|----------|
| Question answered | "What's in this project?" | "What does the AI need right now?" |
| Parser | JavaParser | SCIP (industry standard) |
| Languages | Java | **Java validated**; SCIP path for others later |
| Output | Full AST SQLite | Pruned stub **text** (`java-stub` or `stubborn-dsl`) |
| Token awareness | No | Core KPI |

They complement each other. Stubborn does not replace java-ast-ssot for migration crosswalk or Explorer.

## Privacy contract

**Included:** declarations, signatures, optional Javadoc (`--javadoc summary|full`)  
**Excluded:** method bodies, field initializers, annotation attribute values with business data

## Status

**Beta `0.10.0b2` (Java-first for code weave, source-neutral for contract graph)** — see [BETA.md](BETA.md).

Built with **architecture-led, AI-assisted development** — see [DEVELOPMENT-MODEL.md](DEVELOPMENT-MODEL.md).
