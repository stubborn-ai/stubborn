# Development model

Stubborn is built as an **architecture-led, AI-assisted** product. The goal is not to ship “an AI” as the deliverable, but to use AI as the primary **implementation engine** while the human owner retains **architecture, contracts, and proof obligations**.

The repo is meant to be **read as well as used**: ADRs, E2E cases, and CI guards document intent; the code is ordinary, reviewable Python.

## Roles

### Developer (human)

Responsible for:

- **Architecture** — pipeline shape (ingest → store → prune → weave), repo layout, public API surface
- **Boundary protocols** — SQLite schema, SCIP ingest contracts, CLI/MCP semantics, output format grammars ([ADR index](adr/README.md))
- **Acceptance criteria** — core fixture tests here; compression KPIs, neighbor guards, and Docker E2E cases in [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo)
- **Final judgment** — merge when deterministic gates pass (pytest, ruff, CI E2E, verify scripts)
- **Decision records** — material changes captured as ADRs before or alongside bulk implementation

The developer does **not** need to hand-write every line. The developer owns **intent, structure, and what “correct” means**.

### AI (implementation partner)

Used for:

- Scaffolding modules, tests, workflows, and documentation
- Implementing features against agreed contracts (ingest, weavers, MCP tools)
- Refactors, renames, and cross-repo doc updates under human direction
- Exploring edge cases — output always lands as **reviewable source** in the repo

AI is a tool in **building** Stubborn. Stubborn itself does **not** call LLMs at runtime; it compiles symbol graphs into deterministic stub text for *other* agents to consume.

## Deterministic deliverables

Core pipeline targets **reproducible execution**:

| Stage | Artifact | Proof |
|-------|----------|-------|
| Ingest | `symbols.db` from SCIP | Unit tests + fixture indexes |
| Context | `java-stub` / `stubborn-dsl` text | Same DB + target + budget → same output |
| KPI | `metrics` compression ratio | fixture tests here; demo baselines in [BETA.md](BETA.md) and `stubborn-demo` |
| CI guard | Neighbor type sets | `stubborn-demo` E2E guards |
| Reconcile | Symbol diff | `stubborn diff` exit codes |

Given the same SCIP index, target `stable_id`, and budget options, `context` output is **stable** (no embeddings, no model calls inside Stubborn).

Optional **downstream** LLM use (Cursor, Copilot, custom agents) is out of scope for this repo’s determinism guarantee.

## Boundary protocols

A **boundary protocol** is a published contract at each tool boundary:

1. **Input** — supported SCIP formats ([SCIP-INGEST.md](SCIP-INGEST.md))
2. **Store** — schema v3 ([`v3.sql`](../src/stubborn/store/schema/v3.sql))
3. **Output** — weave formats and version headers ([STUBBORN-DSL.md](STUBBORN-DSL.md))
4. **Agent surface** — MCP tool schemas ([MCP.md](MCP.md))
5. **Errors** — fail-closed CLI; missing symbols or budget overrun surfaced explicitly

Protocols are enforced by tests and CI — not convention alone.

## Relationship to anchor-migration

[anchor-migration](https://github.com/anchor-migration/migration-hub) follows the same **architecture-led, AI-assisted** development model for legacy modernization SSOT tooling. Stubborn is an **independent** repo under [stubborn-ai](https://github.com/stubborn-ai) with the same engineering philosophy but a different product scope (LLM context compiler, not migration pipeline).

Weak coupling rules: [ADR-008](adr/ADR-008-weak-coupling-ecosystem.md). Optional consumer pattern: [INTEGRATION.md](INTEGRATION.md).

## Related

- [adr/README.md](adr/README.md) — architecture decisions
- [POSITIONING.md](POSITIONING.md) — what Stubborn is / is not
- [BETA.md](BETA.md) — beta scope and known limitations
