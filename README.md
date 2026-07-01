# Stubborn

**Deterministic code context from symbol graphs — not vector search.**

> **Status: Beta (Java-first)** — release **`0.9.0b1`** · [BETA.md](docs/BETA.md)

Stubborn compiles a live codebase into **type-safe, privacy-preserving stub text** for LLMs and agents. It uses [SCIP](https://github.com/sourcegraph/scip) symbol indexes and dependency graphs instead of vector chunking, so context is **stubborn**: exact, reproducible, and stripped of method bodies.

Independent project under [stubborn-ai](https://github.com/stubborn-ai). **Not migration-only** — any live project benefits. Optional integration with [anchor-migration](https://github.com/anchor-migration/migration-hub) (see [examples/migration-bridge](examples/migration-bridge/)).

## Why Stubborn?

| Problem | Vector RAG | Stubborn |
|---------|------------|---------------|
| Type hallucinations | Common | Stub signatures from symbol graph |
| Token cost | Full files / arbitrary chunks | Pruned declaration stubs (~80–90% savings target) |
| Privacy | May leak business logic | No method bodies by design |
| Reproducibility | Embedding drift | Same SCIP → same context |

**Stub** = skeleton declarations (like header files).  
**Stubborn** = refuses to guess — only ships what the symbol graph proves.

## Use cases

- **Copilot / Cursor agents** — `getContext(class)` before code generation
- **Large-repo onboarding** — dependency skeleton for one target symbol
- **PR semantic audit** — `diff` two SCIP indexes after a refactor
- **Legacy migration** — optional consumer of [anchor-migration](https://github.com/anchor-migration/migration-hub) (see [examples/migration-bridge](examples/migration-bridge/))

## Requirements

- Python 3.11+ (or use [Docker](docker/README.md))
- A SCIP index for your project (e.g. [scip-java](https://github.com/sourcegraph/scip-java))

### Docker quick start

```bash
docker compose build
docker compose run --rm e2e    # demo-spring E2E
docker compose run --rm petclinic-e2e  # spring-petclinic scale-up
docker compose run --rm cli --help
```

See [docker/README.md](docker/README.md).

## Installation

```bash
git clone https://github.com/stubborn-ai/stubborn.git
cd stubborn
pip install -e ".[dev]"
```

## Quick start

**Full E2E with a modern Spring Boot demo:** see [examples/demo-spring](examples/demo-spring/).

### 1. Index symbols

```bash
# Binary SCIP from scip-java (recommended)
anchor-stubborn index --scip index.scip --out ./metadata/symbols.db

# Or use the bundled fixture while bootstrapping
anchor-stubborn index \
  --scip examples/fixtures/minimal.scip \
  --out ./metadata/symbols.db
```

### 2. Inspect

```bash
anchor-stubborn info ./metadata/symbols.db
```

### 3. Get LLM context for a target symbol

```bash
anchor-stubborn context ./metadata/symbols.db \
  --target "semanticdb maven com/example/OrderService#process()." \
  --out ./context/order-service.stub.java

# Compact cross-language format (~fewer tokens):
anchor-stubborn context ./metadata/symbols.db \
  --target "semanticdb maven com/example/OrderService#process()." \
  --format anchor-dsl \
  --out ./context/order-service.anchor-dsl
```

See [docs/ANCHOR-DSL.md](docs/ANCHOR-DSL.md) for the compact cross-language format.

Tune output granularity: `--member-signatures off|target|neighbors|all`, `--javadoc off|summary|full` ([guide](docs/ANCHOR-DSL-GUIDE.md#granularity-switches-token-vs-detail)).

Or use the short CLI alias: `astub`.

### 4. Reconcile before/after (CI-friendly)

```bash
anchor-stubborn diff ./metadata/before.db ./metadata/after.db
# exit 1 if symbols are missing
```

### 5. MCP server (Cursor / agents)

```bash
pip install -e ".[mcp]"
export ANCHOR_STUBBORN_DB=./metadata/symbols.db
anchor-stubborn mcp
```

Tools: `get_context`, `list_symbols`, `metrics`. See [docs/MCP.md](docs/MCP.md) for Cursor configuration.

## CLI

| Command | Description |
|---------|-------------|
| `init-db` | Create empty SQLite symbol graph |
| `index` | Ingest SCIP (`.scip`, `.scip.ndjson`, or `.json` fixture) |
| `info` | Index run summary |
| `context` | Prune graph → emit LLM context (`--format java-stub` \| `anchor-dsl`) |
| `metrics` | Compression KPI: stub vs full Java sources |
| `mcp` | Run MCP server (stdio) for agents |
| `diff` | Symbol set reconcile (missing/extra) |

## Architecture

```
[Source code] → scip-java / scip-clang / … → index.scip
       ↓
  anchor-stubborn index → SQLite symbol graph
       ↓
  anchor-stubborn context → stub text (java-stub or anchor-dsl)
       ↓
  LLM / Agent / CI
```

SQLite schema: [`src/anchor_stubborn/store/schema/v1.sql`](src/anchor_stubborn/store/schema/v1.sql)

## Roadmap

| Version | Focus |
|---------|-------|
| **0.1** | SQLite schema, JSON fixture ingest, Java stub weaver, CLI shell |
| **0.2** | Binary `.scip` protobuf ingest, `.scip.ndjson`, scip-java compatible |
| **0.3** | Token budget enforcement, `metrics` KPI, weaver quality, Docker CI |
| **0.4** | MCP server (`get_context`, `list_symbols`, `metrics`) |
| **0.5** | Type-neighbor pruning, PR symbol-diff Action, context guard |
| **0.6** | [spring-petclinic](examples/spring-petclinic/) scale-up E2E (~90% savings) |
| **0.7** | [Anchor-DSL](docs/ANCHOR-DSL.md) weaver (`--format anchor-dsl`) |
| **0.8** | Java-first beta track — [BETA.md](docs/BETA.md), demo-spring cases |
| **0.9** | Method signatures, [ANCHOR-DSL-GUIDE](docs/ANCHOR-DSL-GUIDE.md) |
| **0.9.0b1** (now) | **Java-first Beta** — classifier + weave granularity switches |
| **1.0** | Multi-language E2E, stable API |

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/ANCHOR-DSL.md](docs/ANCHOR-DSL.md) | Anchor-DSL grammar |
| [docs/ANCHOR-DSL-GUIDE.md](docs/ANCHOR-DSL-GUIDE.md) | java-stub vs anchor-dsl decision guide |
| [docs/ANCHOR-DSL-LLM.txt](docs/ANCHOR-DSL-LLM.txt) | LLM system-prompt snippet |
| [docs/MCP.md](docs/MCP.md) | Cursor / agent integration |
| [docs/SCIP-INGEST.md](docs/SCIP-INGEST.md) | SCIP ingest |
| [examples/README.md](examples/README.md) | E2E examples |

## Related projects

| Repo | Role |
|------|------|
| [db-metadata](https://github.com/anchor-migration/db-metadata) | Database schema SSOT |
| [java-ast-ssot](https://github.com/anchor-migration/java-ast-ssot) | Full Java AST SSOT (human + rewrite) |
| **stubborn** (this repo) | **LLM context compiler** |
| [migration-hub](https://github.com/anchor-migration/migration-hub) | Program docs; [ADR-010](https://github.com/anchor-migration/migration-hub/blob/main/docs/ADR-010-anchor-stubborn-integration.md) integration contract |

See [docs/POSITIONING.md](docs/POSITIONING.md) and [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

MCP server:

```bash
pip install -e ".[mcp]"
anchor-stubborn mcp
```

## License

MIT — see [LICENSE](LICENSE).
