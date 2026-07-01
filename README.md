# Stubborn

**Deterministic code context from symbol graphs — not vector search.**

> **Status: Beta (Java-first)** — release **`0.9.0b3`** · [BETA.md](docs/BETA.md) · [CHANGELOG](CHANGELOG.md)

Stubborn compiles a live codebase into **type-safe, privacy-preserving stub text** for LLMs and agents. It uses [SCIP](https://github.com/sourcegraph/scip) symbol indexes and dependency graphs instead of vector chunking, so context is **stubborn**: exact, reproducible, and stripped of method bodies.

Independent project under [stubborn-ai](https://github.com/stubborn-ai). Works with any SCIP-indexed codebase — Spring, monorepos, agents, and CI.

This repo is a **personal showcase of architecture-led, AI-assisted engineering**: the developer defines system design, boundary protocols, and acceptance criteria; AI implements most of the code; the shipped artifact is **deterministic Python** — reproducible, test-gated, and verifiable (same SCIP → same context).

> [Development model →](docs/DEVELOPMENT-MODEL.md) — human vs AI roles, deterministic core, boundary protocols.

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
- **Refactor / legacy modernization** — scoped context for large Java estates (see [examples/migration-bridge](examples/migration-bridge/))

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

**PyPI:** `stubborn-stub` · **CLI:** `stubborn` (alias: `stub`)

```bash
pip install stubborn-stub[mcp]
```

From source (development):

```bash
git clone https://github.com/stubborn-ai/stubborn.git
cd stubborn
pip install -e ".[dev]"
```

### Try in 30 seconds (no Java required)

Uses the bundled minimal SCIP fixture — no JDK, Maven, or scip-java needed:

```bash
pip install stubborn-stub
stubborn index --scip examples/fixtures/minimal.scip --out /tmp/symbols.db
stubborn info /tmp/symbols.db
stubborn context /tmp/symbols.db \
  --target "semanticdb maven com/example/OrderService#" \
  --out /tmp/order-service.stub.java
```

## Quick start

**Full E2E with a modern Spring Boot demo:** see [examples/demo-spring](examples/demo-spring/).

### 1. Index symbols

```bash
# Binary SCIP from scip-java (recommended)
stubborn index --scip index.scip --out ./metadata/symbols.db

# Or use the bundled fixture while bootstrapping
stubborn index \
  --scip examples/fixtures/minimal.scip \
  --out ./metadata/symbols.db
```

### 2. Inspect

```bash
stubborn info ./metadata/symbols.db
```

### 3. Get LLM context for a target symbol

```bash
stubborn context ./metadata/symbols.db \
  --target "semanticdb maven com/example/OrderService#process()." \
  --out ./context/order-service.stub.java

# Compact cross-language format (~fewer tokens):
stubborn context ./metadata/symbols.db \
  --target "semanticdb maven com/example/OrderService#process()." \
  --format stubborn-dsl \
  --out ./context/order-service.stubborn-dsl
```

See [docs/STUBBORN-DSL.md](docs/STUBBORN-DSL.md) for the compact cross-language format.

Tune output granularity: `--member-signatures off|target|neighbors|all`, `--javadoc off|summary|full` ([guide](docs/STUBBORN-DSL-GUIDE.md#granularity-switches-token-vs-detail)).

Or use the short CLI alias: `stub`.

### 4. Reconcile before/after (CI-friendly)

```bash
stubborn diff ./metadata/before.db ./metadata/after.db
# exit 1 if symbols are missing
```

### 5. MCP server (Cursor / agents)

```bash
pip install stubborn-stub[mcp]
export STUBBORN_DB=./metadata/symbols.db
stubborn mcp
```

Tools: `get_context`, `list_symbols`, `metrics`. See [docs/MCP.md](docs/MCP.md) for Cursor configuration.

## CLI

| Command | Description |
|---------|-------------|
| `init-db` | Create empty SQLite symbol graph |
| `index` | Ingest SCIP (`.scip`, `.scip.ndjson`, or `.json` fixture) |
| `info` | Index run summary |
| `context` | Prune graph → emit LLM context (`--format java-stub` \| `stubborn-dsl`) |
| `metrics` | Compression KPI: stub vs full Java sources |
| `mcp` | Run MCP server (stdio) for agents |
| `diff` | Symbol set reconcile (missing/extra) |

## Architecture

Design rationale is recorded as [Architecture Decision Records (docs/adr/)](docs/adr/README.md). Pipeline overview:

```
[Source code] → scip-java / scip-clang / … → index.scip
       ↓
  stubborn index → SQLite symbol graph
       ↓
  stubborn context → stub text (java-stub or stubborn-dsl)
       ↓
  LLM / Agent / CI
```

SQLite schema: [`src/stubborn/store/schema/v1.sql`](src/stubborn/store/schema/v1.sql)

## Roadmap

| Version | Focus |
|---------|-------|
| **0.1** | SQLite schema, JSON fixture ingest, Java stub weaver, CLI shell |
| **0.2** | Binary `.scip` protobuf ingest, `.scip.ndjson`, scip-java compatible |
| **0.3** | Token budget enforcement, `metrics` KPI, weaver quality, Docker CI |
| **0.4** | MCP server (`get_context`, `list_symbols`, `metrics`) |
| **0.5** | Type-neighbor pruning, PR symbol-diff Action, context guard |
| **0.6** | [spring-petclinic](examples/spring-petclinic/) scale-up E2E (~90% savings) |
| **0.7** | [Stubborn-DSL](docs/STUBBORN-DSL.md) weaver (`--format stubborn-dsl`) |
| **0.8** | Java-first beta track — [BETA.md](docs/BETA.md), demo-spring cases |
| **0.9** | Method signatures, [STUBBORN-DSL-GUIDE](docs/STUBBORN-DSL-GUIDE.md) |
| **0.9.0b3** (now) | **Standalone cleanup** — rename debt removed, ruff CI, CLI smoke tests |
| **0.9.0b2** | **Java-first Beta** — classifier + weave granularity switches |
| **1.0** | Multi-language E2E, stable API |

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/DEVELOPMENT-MODEL.md](docs/DEVELOPMENT-MODEL.md) | Architecture-led, AI-assisted development model |
| [docs/adr/README.md](docs/adr/README.md) | Architecture Decision Records (design rationale) |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/STUBBORN-DSL.md](docs/STUBBORN-DSL.md) | Stubborn-DSL grammar |
| [docs/STUBBORN-DSL-GUIDE.md](docs/STUBBORN-DSL-GUIDE.md) | java-stub vs stubborn-dsl decision guide |
| [docs/STUBBORN-DSL-LLM.txt](docs/STUBBORN-DSL-LLM.txt) | LLM system-prompt snippet |
| [docs/MCP.md](docs/MCP.md) | Cursor / agent integration |
| [docs/SCIP-INGEST.md](docs/SCIP-INGEST.md) | SCIP ingest |
| [examples/README.md](examples/README.md) | E2E examples |

## Optional ecosystem integrations

Stubborn is standalone. Some teams also use it alongside the [anchor-migration](https://github.com/anchor-migration/migration-hub) program:

| Repo | Role |
|------|------|
| **stubborn** (this repo) | **LLM context compiler** |
| [migration-hub](https://github.com/anchor-migration/migration-hub) | Optional program docs — [integration guide](docs/INTEGRATION.md) |
| [java-ast-ssot](https://github.com/anchor-migration/java-ast-ssot) | Full Java AST SSOT (complementary) |
| [db-metadata](https://github.com/anchor-migration/db-metadata) | Database schema SSOT (complementary) |

See [docs/POSITIONING.md](docs/POSITIONING.md).

## Development

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests
ruff format --check src tests
```

MCP server:

```bash
pip install -e ".[mcp]"
stubborn mcp
```

## License

MIT — see [LICENSE](LICENSE).
