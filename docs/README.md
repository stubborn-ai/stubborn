# Documentation index

**PyPI package:** `stubborn-stub` · **version:** `0.9.0b2` (Beta) · **CLI:** `stubborn`

| Doc | Audience | Contents |
|-----|----------|----------|
| [BETA.md](BETA.md) | Release owners | Java-first beta checklist and known limitations |
| [POSITIONING.md](POSITIONING.md) | Architects | What Stubborn is / is not; ecosystem placement |
| [INTEGRATION.md](INTEGRATION.md) | Optional adopters | How anchor-migration consumes Stubborn |
| [SCIP-INGEST.md](SCIP-INGEST.md) | Index authors | Supported SCIP formats and ingest behavior |
| [MCP.md](MCP.md) | Agent / Cursor users | MCP tools, config, workflows |
| [STUBBORN-DSL-GUIDE.md](STUBBORN-DSL-GUIDE.md) | Prompt authors | When to use java-stub vs stubborn-dsl |
| [STUBBORN-DSL.md](STUBBORN-DSL.md) | LLM context authors | Stubborn-DSL v1 grammar and CLI usage |
| [STUBBORN-DSL-LLM.txt](STUBBORN-DSL-LLM.txt) | Prompt engineers | Short system-prompt snippet for `format=stubborn-dsl` |

## Output formats

| Format | CLI / MCP `format` | When to use |
|--------|-------------------|-------------|
| Java stub | `java-stub` (default) | Java / Spring code generation |
| Stubborn-DSL | `stubborn-dsl` | Lower tokens, graph-first reasoning; includes inline `# Guide` |

Both formats share the same prune step and privacy contract (declarations only, no method bodies).

**Weave granularity** (CLI / API / MCP): `--member-signatures` and `--javadoc` — see [STUBBORN-DSL-GUIDE.md](STUBBORN-DSL-GUIDE.md#granularity-switches-token-vs-detail).

## Examples

| Path | Description |
|------|-------------|
| [examples/demo-spring](../examples/demo-spring/) | Primary in-repo E2E (~14 files, ~81% savings) |
| [examples/spring-petclinic](../examples/spring-petclinic/) | Scale-up E2E vs upstream PetClinic (~375 symbols, ~90% savings) |
| [examples/migration-bridge](../examples/migration-bridge/) | Optional anchor-migration consumer pattern |
| [docker/README.md](../docker/README.md) | Reproducible Docker toolchain |

## External

- [INTEGRATION.md](INTEGRATION.md) — optional anchor-migration program integration
