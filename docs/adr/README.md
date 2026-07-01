# Architecture Decision Records (ADR)

Stubborn records **significant, hard-to-reverse** design choices here. Each ADR captures context, the decision, and what we rejected — so future contributors (and future you) do not have to reconstruct rationale from code or scattered docs.

This project is built for **use and for reading**: ADRs are part of the public design story, not internal meeting notes.

## Index

| ADR | Status | Title |
|-----|--------|-------|
| [ADR-001](ADR-001-scip-as-machine-index.md) | Accepted | SCIP as the machine index |
| [ADR-002](ADR-002-sqlite-symbol-graph-ssot.md) | Accepted | SQLite symbol graph as SSoT |
| [ADR-003](ADR-003-type-neighbor-pruning.md) | Accepted | Type-neighbor BFS pruning with token budget |
| [ADR-004](ADR-004-privacy-contract-declarations-only.md) | Accepted | Privacy contract: declarations only |
| [ADR-005](ADR-005-dual-output-formats.md) | Accepted | Dual output formats: `java-stub` and `stubborn-dsl` |
| [ADR-006](ADR-006-mcp-first-agent-integration.md) | Accepted | MCP-first agent integration |
| [ADR-007](ADR-007-java-first-beta-scope.md) | Accepted | Java-first beta scope |
| [ADR-008](ADR-008-weak-coupling-ecosystem.md) | Accepted | Weak coupling to optional ecosystem consumers |

## Status legend

| Status | Meaning |
|--------|---------|
| **Accepted** | In effect |
| **Superseded** | Replaced by a later ADR (link included) |
| **Deprecated** | No longer recommended; kept for history |

## When to write a new ADR

Add one when a change:

- Alters the pipeline shape (ingest → store → prune → weave)
- Changes the privacy or determinism contract
- Adds a new output format or breaks an existing grammar version
- Chooses between approaches with meaningful trade-offs (not “which linter”)

Skip ADRs for routine refactors, dependency bumps, or CI tweaks — [CHANGELOG.md](../../CHANGELOG.md) is enough.

## Template

```markdown
# ADR-NNN: Title

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Deciders:** …

## Context

What problem are we solving? What constraints apply?

## Decision

What we chose, in one or two paragraphs.

## Consequences

### Positive
- …

### Negative / trade-offs
- …

## Alternatives considered

| Option | Why not |
|--------|---------|
| … | … |

## References

- Links to code, docs, issues
```

## Related docs (not ADRs)

| Doc | Role |
|-----|------|
| [DEVELOPMENT-MODEL.md](../DEVELOPMENT-MODEL.md) | Architecture-led, AI-assisted build; human vs AI roles |
| [POSITIONING.md](../POSITIONING.md) | Product positioning (what it is / is not) |
| [BETA.md](../BETA.md) | Release scope and KPI baselines |
| [SCIP-INGEST.md](../SCIP-INGEST.md) | Ingest behavior spec |
| [STUBBORN-DSL.md](../STUBBORN-DSL.md) | Stubborn-DSL grammar spec |
| [INTEGRATION.md](../INTEGRATION.md) | Optional anchor-migration consumer pattern |

External integration contract (another repo): [migration-hub ADR-010](https://github.com/anchor-migration/migration-hub/blob/main/docs/ADR-010-anchor-stubborn-integration.md).
