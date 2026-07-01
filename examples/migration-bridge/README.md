# Migration bridge example

How [anchor-migration](https://github.com/anchor-migration/migration-hub) can consume Stubborn without tight coupling.

## Scenario

Migrating `AccountControllerBean` (EJB session) → Spring `@Service`. The LLM needs surrounding types but not full method bodies.

**Formal runbook:** [examples/dukesbank](../dukesbank/) (E2E scripts, case docs, Docker `dukesbank-e2e`). This folder is the minimal consumer sketch.

## Steps

```bash
# In the legacy Java repo (with scip-java configured)
scip-java index
# produces index.scip (binary protobuf)

# Index into Stubborn SQLite
stubborn index --scip index.scip --out metadata/context.db

# Emit privacy-safe context (Java stub)
stubborn context metadata/context.db \
  --target "semanticdb maven com/sun/ebank/ejb/account/AccountControllerBean#" \
  --out account-controller.stub.java

# Or compact graph format
stubborn context metadata/context.db \
  --target "semanticdb maven com/sun/ebank/ejb/account/AccountControllerBean#" \
  --format stubborn-dsl \
  --out account-controller.stubborn-dsl
```

Paste the output into your agent prompt instead of entire source trees. For `stubborn-dsl`, see [docs/STUBBORN-DSL-LLM.txt](../../docs/STUBBORN-DSL-LLM.txt).

Or use MCP: `get_context` with the same `target` and optional `format`.

## What stays in migration repos

| Task | Tool |
|------|------|
| Full code SSOT + EJB profiles | java-ast-ssot |
| Schema SSOT | db-metadata |
| Crosswalk + Explorer | java-ast-ssot + anchor-explorer |
| **LLM context only** | **stubborn** |
| Apply rewrites | rewrite-recipes |

## CI hook

Symbol reconcile after refactors:

```yaml
- run: stubborn diff metadata/before.db metadata/after.db
```

See [pr-symbol-diff.yml](../../.github/workflows/pr-symbol-diff.yml) and [docs/INTEGRATION.md](../../docs/INTEGRATION.md).
