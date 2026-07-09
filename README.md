# Stubborn

**Deterministic code context from symbol graphs — for SCIP-indexed codebases.**

> **Status: Beta (Java-first)** — release **`0.9.0b5`** · [BETA.md](docs/BETA.md) · [POSITIONING.md](docs/POSITIONING.md) · [CHANGELOG](CHANGELOG.md)

Stubborn compiles a **SCIP symbol index** into **type-safe, privacy-preserving stub text** for LLMs and agents. Same index + target + options → same context: reproducible, token-bounded, and stripped of method bodies.

**Primary fit:** Java / Spring repos (especially legacy modernization) where teams already run or can run **scip-java**. **Also:** Cursor/MCP users with a `symbols.db` who want deterministic context — not a zero-config repo map.

Independent project under [stubborn-ai](https://github.com/stubborn-ai) ([program map](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/START-HERE.md)). Full positioning: [docs/POSITIONING.md](docs/POSITIONING.md).

This repo is a **personal showcase of architecture-led, AI-assisted engineering**: the developer defines system design, boundary protocols, and acceptance criteria; AI implements most of the code; the shipped artifact is **deterministic Python** — reproducible, test-gated, and verifiable (same SCIP → same context).

> [Development model →](docs/DEVELOPMENT-MODEL.md) — human vs AI roles, deterministic core, boundary protocols.

## Why Stubborn?

Real pain points: **type hallucinations** when LLMs lack declarations, **token waste** from whole files, **privacy** from leaking implementations, **non-reproducible** embedding chunks.

Stubborn addresses these when you already have (or can build) a **SCIP index**. Compare on three axes — not “us vs vector RAG” alone:

| | Stubborn | Vector chunk RAG | Low-friction symbol maps (e.g. Aider repo-map) |
|---|----------|------------------|-----------------------------------------------|
| **Determinism** | Same SCIP → same stub | Chunk / embedding drift | Varies |
| **Type structure** | Symbol graph + signatures | Arbitrary text spans | Repo structure / tags |
| **Setup friction** | **SCIP index required** | Index / embed pipeline | **Open repo** |
| **Token KPI** | Built-in `metrics`, ~80–90% vs sources (Java E2E) | Unpredictable | Not a design goal |
| **Privacy** | No method bodies by design | May include full files | Full files possible |
| **CI reconcile** | `diff`, symbol guards | Hard to baseline | Uncommon |

**Stub** = skeleton declarations (like header files).  
**Stubborn** = compiles symbol graphs into bounded stub text; use **`--prune-mode strict`** when you want SCIP-proven neighbors only ([ADR-003](docs/adr/ADR-003-type-neighbor-pruning.md)).

## Use cases

**Primary (Java / Spring + SCIP workflow):**

- **Legacy / modernization** — scoped context for large estates; runnable validation lives in [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo)
- **PR semantic audit** — `diff` two SCIP indexes; CI symbol guards
- **Program runbooks** — reproducible stub artifacts with compression KPIs

**Secondary (agents / individuals):**

- **Cursor / MCP** — `get_context` before codegen on a pre-built `symbols.db`
- **Large-repo onboarding** — dependency skeleton for one target symbol

Start with [30-second fixture](#try-in-30-seconds-no-java-required) or [Docker E2E](#docker-quick-start); Docker is the primary reproducible path. On Windows, use **WSL2** for shell-heavy work and keep PowerShell host scripts as a fallback, not a second primary path (see [Requirements](#requirements)).

## Requirements

Recommended local shell:

- **Linux shell**: any bash-compatible shell, including Ubuntu and macOS
- **Windows**: **WSL2** for Docker and bash-heavy workflows; PowerShell only as a fallback tier

- Python 3.11+ (or use [Docker](docker/README.md))
- A **SCIP index** for your project — Stubborn does not index source directly

| Goal | You need |
|------|----------|
| Try Stubborn (no Java) | Bundled JSON fixture only — [below](#try-in-30-seconds-no-java-required) |
| Real Java / Spring repo | **[scip-java](https://github.com/sourcegraph/scip-java)** (or CI that produces `index.scip`) + `stubborn-stub[scip]` + `stubborn index` |
| Reproduce project E2E | Docker Desktop — [docker/README.md](docker/README.md) |

**Beta scope:** weave quality and KPIs are **Java-validated**. Other SCIP languages may ingest; output quality is not guaranteed until language-specific E2E ships ([BETA.md](docs/BETA.md)).

## Execution tiers

| Tier | Use when | Typical entrypoints |
|------|----------|---------------------|
| Docker | You want the same environment on Windows, Linux, and macOS | `docker compose build`, `docker compose run --rm shell`, `docker compose run --rm cli` |
| WSL/bash | You want the fastest local loop on a Unix-like shell | `pytest`, `ruff`, host scripts under `stubborn-demo/**/scripts/*.sh` |
| PowerShell fallback | You are on Windows host and need a thin fallback path | Historical `*.ps1` scripts from git history, or thin wrappers that call the same targets |

### Docker quick start

```bash
docker compose build
docker compose run --rm cli --help
docker compose run --rm shell -lc \
  "stubborn index --scip examples/fixtures/minimal.scip --out /tmp/symbols.db && stubborn info /tmp/symbols.db"
```

See [docker/README.md](docker/README.md). Runnable Java demos and E2E validation live in [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo).

## Installation

**PyPI:** `stubborn-stub` · **CLI:** `stubborn` (alias: `stub`)

```bash
pip install stubborn-stub
```

Binary/NDJSON SCIP ingest needs the optional protobuf runtime:

```bash
pip install "stubborn-stub[scip]"
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
stubborn index --scip examples/fixtures/minimal.json --out /tmp/symbols.db
stubborn info /tmp/symbols.db
stubborn context /tmp/symbols.db \
  --target "semanticdb maven com/example/OrderService#" \
  --out /tmp/order-service.stub.java
```

## Quick start

**Full E2E with a modern Spring Boot demo:** see [`stubborn-demo/demo-spring`](https://github.com/stubborn-ai/stubborn-demo/tree/main/demo-spring).

### 1. Index symbols

```bash
# Binary SCIP from scip-java (recommended; requires stubborn-stub[scip])
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

### Optional: index explicit service contracts

Schema v4 can store explicit REST contract evidence separately from SCIP facts:

```bash
stubborn index-contract \
  --manifest contracts/http.json \
  --out ./metadata/symbols.db

stubborn index-openapi \
  --openapi openapi.yml \
  --service customers-service \
  --version v1 \
  --out ./metadata/symbols.db
```

The first manifest format is intentionally explicit: endpoints declare
`service`, `version`, `method`, `path`, and `providers`/`consumers` bindings.
Bindings may reference existing code symbols by `code_stable_id`, or by
`repo` + `display_name` inside a workspace. Contract evidence is rendered in
`--format stubborn-dsl` under a separate `contracts:` block; Java stubs remain
Java-shaped.

`index-openapi` is endpoint/schema ingest only. It does not infer provider or
consumer code bindings from annotations, URLs, or client interfaces. JSON input
uses only the core package; YAML input requires `pip install stubborn-stub[openapi]`.

Binary `.scip` and `.scip.ndjson` inputs require `pip install stubborn-stub[scip]`.

**Choose output format:**

| Project | Suggested `--format` |
|---------|---------------------|
| Pure Java / Spring codegen | `java-stub` (default) |
| Mixed-language or token-sensitive / graph-first | `stubborn-dsl` |

Tune output granularity: `--member-signatures off|target|neighbors|all`, `--javadoc off|summary|full` ([guide](docs/STUBBORN-DSL-GUIDE.md#granularity-switches-token-vs-detail)).

**Choose neighbor expansion (`--prune-mode`):**

| Mode | When |
|------|------|
| `smart` (default) | Richest type neighbors; CI guards assume this |
| `strict` | SCIP-proven edges only — no signature heuristics |
| `fast` | Smaller neighborhood + no heuristics — tight token budget |

Or use the short CLI alias: `stub`.

### 4. Reconcile before/after (CI-friendly)

```bash
stubborn diff ./metadata/before.db ./metadata/after.db
# exit 1 if symbols are missing
```

### 5. MCP server (Cursor / agents)

Use the separate **[stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)** package:

```bash
pip install stubborn-mcp
export STUBBORN_DB=./metadata/symbols.db
stubborn-mcp
```

Tools: `get_context`, `list_symbols`, `metrics`. See [stubborn-mcp docs](https://github.com/stubborn-ai/stubborn-mcp/blob/main/docs/MCP.md).

### 6. Setup diagnostics (federated doctor)

Read-only checks per package ([ADR-015](docs/adr/ADR-015-federated-doctor-diagnostics.md)) — no ingest, merge, or **schema migration** on `symbols.db`:

```bash
stubborn doctor --json
stubborn-mcp doctor        # if using agents
stubborn-watch doctor      # if using dev watch loop
stubborn-status --json     # aggregate installed packages' doctor reports
```

Full checklist: [stubborn-hub DEMO-LAUNCHERS](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md).

## CLI

| Command | Description |
|---------|-------------|
| `init-db` | Create empty SQLite symbol graph |
| `workspace` | Initialize/register multi-repo workspace metadata |
| `index` | Ingest SCIP (`.scip`, `.scip.ndjson`, or `.json` fixture); use `--workspace`/`--repo` for multi-repo views |
| `index-contract` | Ingest an explicit contract manifest into schema v4 contract evidence tables |
| `index-openapi` | Ingest OpenAPI 3.x endpoints/schemas without inferring code bindings |
| `info` | Index run summary |
| `context` | Prune graph → emit LLM context (`--workspace` can query latest runs across repos) |
| `list-contracts` | Browse contract endpoint stable IDs and schema constraints |
| `list-symbols` | Browse symbols in a legacy, repo, or workspace view |
| `metrics` | Compression KPI: stub vs full Java sources |
| `diff` | Symbol set reconcile (missing/extra) |
| `doctor` | Read-only setup diagnostics — DB health, project signals, delegation hints ([ADR-015](docs/adr/ADR-015-federated-doctor-diagnostics.md)) |

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

SQLite schema: [`src/stubborn/store/schema/v4.sql`](src/stubborn/store/schema/v4.sql)

## Roadmap

| Version | Focus |
|---------|-------|
| **0.1** | SQLite schema, JSON fixture ingest, Java stub weaver, CLI shell |
| **0.2** | Binary `.scip` protobuf ingest, `.scip.ndjson`, scip-java compatible |
| **0.3** | Token budget enforcement, `metrics` KPI, weaver quality, Docker CI |
| **0.4** | MCP server (`get_context`, `list_symbols`, `metrics`) |
| **0.5** | Type-neighbor pruning, PR symbol-diff Action, context guard |
| **0.6** | spring-petclinic scale-up E2E (~90% savings; now maintained in [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo)) |
| **0.7** | [Stubborn-DSL](docs/STUBBORN-DSL.md) weaver (`--format stubborn-dsl`) |
| **0.8** | Java-first beta track — [BETA.md](docs/BETA.md), demo-spring cases |
| **0.9** | Method signatures, [STUBBORN-DSL-GUIDE](docs/STUBBORN-DSL-GUIDE.md) |
| **0.9.0b5** (now) | **Source-neutral contracts** — contract graph evidence, `index-openapi`, `index-contract`, optional SCIP runtime |
| **0.9.0b3** | Standalone cleanup — rename debt removed, ruff CI, CLI smoke tests |
| **0.9.0b2** | **Java-first Beta** — classifier + weave granularity switches |
| **1.0** | Multi-language E2E, stable API |

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/DEVELOPMENT-MODEL.md](docs/DEVELOPMENT-MODEL.md) | Architecture-led, AI-assisted development model |
| [docs/adr/README.md](docs/adr/README.md) | Architecture Decision Records (design rationale) |
| [docs/POSITIONING.md](docs/POSITIONING.md) | Product positioning — audience, competitors, honest scope |
| [docs/BETA.md](docs/BETA.md) | Beta checklist, limitations, KPI baselines |
| [docs/STUBBORN-DSL.md](docs/STUBBORN-DSL.md) | Stubborn-DSL grammar |
| [docs/STUBBORN-DSL-GUIDE.md](docs/STUBBORN-DSL-GUIDE.md) | java-stub vs stubborn-dsl decision guide |
| [docs/STUBBORN-DSL-LLM.txt](docs/STUBBORN-DSL-LLM.txt) | LLM system-prompt snippet |
| [docs/MCP.md](docs/MCP.md) | Cursor / agent integration |
| [docs/adr/ADR-015-federated-doctor-diagnostics.md](docs/adr/ADR-015-federated-doctor-diagnostics.md) | Federated `doctor` setup diagnostics |
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

MCP server ([stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)):

```bash
pip install -e "../stubborn-mcp"
stubborn-mcp
```

## License

MIT — see [LICENSE](LICENSE).
