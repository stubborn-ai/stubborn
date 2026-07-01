# Optional: anchor-migration program

Stubborn is a **standalone** product. The [anchor-migration](https://github.com/anchor-migration/migration-hub) program is one optional consumer — not the owner of this repo.

## When migration uses Stubborn

Before asking an LLM to propose rewrite mappings or recipe changes:

```bash
# 1. Generate SCIP (scip-java in the target repo)
# 2. Index
stubborn index --scip index.scip --out metadata/code-context.db

# 3. Context for a migration target class (Java stub — familiar to codegen models)
stubborn context metadata/code-context.db \
  --target "semanticdb maven com/sun/ebank/ejb/account/AccountControllerBean#" \
  --out /tmp/account-controller.stub.java

# Or compact graph format (fewer tokens)
stubborn context metadata/code-context.db \
  --target "semanticdb maven com/sun/ebank/ejb/account/AccountControllerBean#" \
  --format stubborn-dsl \
  --out /tmp/account-controller.stubborn-dsl
```

Feed the output to the LLM instead of raw sources. For `stubborn-dsl`, paste [STUBBORN-DSL-LLM.txt](STUBBORN-DSL-LLM.txt) into the system prompt (or rely on the embedded `# Guide` header).

Or use the MCP server (`stubborn mcp`) so agents call `get_context` with `format: "java-stub"` or `"stubborn-dsl"` — see [MCP.md](MCP.md).

Tune weave output: `--member-signatures off|target|neighbors|all` and `--javadoc off|summary|full` on `context` / `metrics` (and MCP `get_context`).

## When migration does NOT use Stubborn

- Full AST export for Explorer → **java-ast-ssot**
- Schema ↔ code crosswalk → **java-ast-ssot crosswalk** + **db-metadata**
- Applying rewrites → **rewrite-recipes** + OpenRewrite
- Parity testing → **parity-verify** (separate program tooling)

## Pipeline diagram (consumer view)

```
                    ┌─────────────────────┐
                    │   stubborn   │
                    └──────────┬──────────┘
                               │ stub / stubborn-dsl text
     ┌─────────────────────────┼─────────────────────────┐
     ▼                         ▼                         ▼
 LLM mapping draft      rewrite-recipes design      PR diff CI
```

Stubborn is **not** drawn inside migration-hub Layers 1–4. It sits above them as shared infrastructure.

## Program contract

Cross-program contract (external): [migration-hub ADR-010](https://github.com/anchor-migration/migration-hub/blob/main/docs/ADR-010-anchor-stubborn-integration.md). This file is the repo-local summary.

## CI hooks (shipped)

| Workflow | Purpose |
|----------|---------|
| `stubborn diff` | Symbol reconcile between two indexes |
| [pr-symbol-diff.yml](../.github/workflows/pr-symbol-diff.yml) | PR guard for symbol regressions |
| [petclinic-e2e.yml](../.github/workflows/petclinic-e2e.yml) | Weekly / manual scale-up E2E |

Example:

```yaml
- run: stubborn diff metadata/before.db metadata/after.db
```

Fails if symbols are missing (exit code 1).

## Weak coupling rules

1. **No compile-time dependency** from Stubborn → rewrite-recipes or java-ast-ssot
2. **Shared conventions only**: stable IDs, SQLite snapshot pattern, reconcile vocabulary
3. **Optional** in any migration runbook — teams can use java-ast-ssot alone when full AST is required
