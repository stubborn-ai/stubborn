# ADR-008: Weak coupling to optional ecosystem consumers

- **Status:** Accepted
- **Documented:** 2026-07-02
- **Deciders:** Stubborn maintainers

## Context

Stubborn originated near the [anchor-migration](https://github.com/anchor-migration/migration-hub) program and shares design patterns (SQLite snapshots, stable IDs, reconcile vocabulary) with repos like **java-ast-ssot** and **db-metadata**.

As an **independent** project under [stubborn-ai](https://github.com/stubborn-ai), it must:

- Install and deliver value **without** migration-hub or OpenRewrite
- Avoid compile-time dependencies on sibling repos
- Remain usable for generic Spring/monorepo/agent workflows

## Decision

**Weak coupling only** — shared conventions, not shared code or mandatory orchestration.

Rules:

1. **No compile-time dependency** from Stubborn → rewrite-recipes, java-ast-ssot, db-metadata, or migration-hub
2. **Optional consumer** pattern documented in [INTEGRATION.md](../INTEGRATION.md)
3. **Cross-program contract** for migration teams lives externally: [migration-hub ADR-010](https://github.com/anchor-migration/migration-hub/blob/main/docs/ADR-010-anchor-stubborn-integration.md); this repo keeps a repo-local summary only
4. **Complementary, not competitive** with java-ast-ssot: full AST / Explorer vs pruned LLM context (see [POSITIONING.md](../POSITIONING.md))

Stubborn’s README leads with standalone value; ecosystem links sit under “Optional ecosystem integrations.”

## Consequences

### Positive

- PyPI package (`stubborn-stub`) is self-contained
- Teams can adopt for Cursor/CI without joining a migration program
- Clear boundary reduces scope creep into rewrite/AST territory

### Negative / trade-offs

- Duplicated *documentation* of integration patterns (hub ADR + INTEGRATION.md)
- Migration users must wire Stubborn into runbooks themselves (Duke's Bank and migration-bridge sketches live in `stubborn-demo`)

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Monorepo with migration-hub** | Couples release cadence; confuses standalone adopters |
| **Hard dependency on java-ast-ssot** | Heavier install; wrong tool for “context for one symbol” |
| **Stubborn owned by migration-hub** | Contradicts independent product under stubborn-ai |

## References

- [INTEGRATION.md](../INTEGRATION.md)
- [POSITIONING.md](../POSITIONING.md)
- [`stubborn-demo/migration-bridge`](https://github.com/stubborn-ai/stubborn-demo/tree/main/migration-bridge)
