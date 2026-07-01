# ADR-007: Java-first beta scope

- **Status:** Accepted
- **Date:** 2026-07-01 (formalized 2026-07-02)
- **Deciders:** Stubborn maintainers

## Context

Stubborn’s architecture is **language-agnostic at ingest** (SCIP supports many languages), but **weave quality** and **E2E validation** require language-specific investment:

- Signature parsing and neighbor heuristics tuned for Java
- Demo apps (Spring Boot, PetClinic, Duke’s Bank)
- Compression KPI baselines agents and docs reference

Shipping “multi-language” without E2E would over-promise and under-deliver.

## Decision

**Beta (`0.9.x`) is Java-first.** We claim production-ready behavior only for the scip-java path validated in CI and examples.

| In scope (beta) | Out of scope until 1.0 |
|-----------------|------------------------|
| scip-java → `.scip` ingest | scip-clang / TypeScript E2E |
| `java-stub` + `stubborn-dsl` weave for Java symbols | Method signatures on all neighbor types by default |
| demo-spring + petclinic + dukesbank cases | Petclinic on every PR (cost) |
| MCP + CLI + Docker toolchain | Model-specific token counting |

PyPI classifier: `Development Status :: 4 - Beta`. Target stable: **1.0** with multi-language E2E and stable public API.

Users may ingest non-Java SCIP experimentally; output quality is **best-effort** until an ADR supersedes this scope.

## Consequences

### Positive

- Honest marketing; KPI numbers are reproducible on Java examples
- CI stays fast enough for every PR (Docker demo-spring + pytest matrix)
- Clear roadmap item for 1.0 ([README.md](../../README.md))

### Negative / trade-offs

- Non-Java early adopters may hit rough weave edges
- “Java-first” requires explaining SCIP generality vs weave specificity

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Declare general availability day one** | No KPI proof; support burden |
| **Java-only ingest** | Rejects valid SCIP; limits future path |
| **Delay beta until all SCIP languages E2E** | Blocks useful Java agent workflows indefinitely |

## References

- [BETA.md](../BETA.md)
- [examples/README.md](../../examples/README.md)
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml)
