# Documentation index

**Program map:** [stubborn-hub](https://github.com/stubborn-ai/stubborn-hub) · **PyPI package:** `stubborn-stub` · **version:** `0.10.0b2` (Beta) · **CLI:** `stubborn`

| Doc | Audience | Contents |
|-----|----------|----------|
| [DEVELOPMENT-MODEL.md](DEVELOPMENT-MODEL.md) | Contributors, readers | Architecture-led, AI-assisted build; deterministic deliverables |
| [adr/README.md](adr/README.md) | Contributors, architects | Architecture Decision Records (ADR index) |
| [BETA.md](BETA.md) | Release owners | Java-first beta checklist and known limitations |
| [POSITIONING.md](POSITIONING.md) | Architects, adopters | Primary/secondary audience; honest comparison; SCIP prerequisite |
| [INTEGRATION.md](INTEGRATION.md) | Optional adopters | How anchor-migration consumes Stubborn |
| [SCIP-INGEST.md](SCIP-INGEST.md) | Index authors | Supported SCIP formats and ingest behavior |
| [CONTRACT-GRAPH.md](CONTRACT-GRAPH.md) | Adapter authors | Contract graph IR, evidence tiers, and REST/OpenAPI boundaries |
| [stubborn-hub CONTRACT-GRAPH-PLAYBOOK](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/CONTRACT-GRAPH-PLAYBOOK.md) | Adopters | Step-by-step mixed workspace ingest and query |
| [MCP.md](MCP.md) | Agent / Cursor users | Pointer to **stubborn-mcp** package |
| [adr/ADR-015-federated-doctor-diagnostics.md](adr/ADR-015-federated-doctor-diagnostics.md) | Adopters, CI owners | Federated read-only `doctor` setup diagnostics |
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
| [examples/fixtures](../examples/fixtures/) | Minimal SCIP fixtures for unit tests and quick starts |
| [stubborn-demo](https://github.com/stubborn-ai/stubborn-demo) | Runnable demos and black-box validation projects |
| [docker/README.md](../docker/README.md) | Reproducible core CLI/toolchain image |

## External

- [INTEGRATION.md](INTEGRATION.md) — optional anchor-migration program integration
