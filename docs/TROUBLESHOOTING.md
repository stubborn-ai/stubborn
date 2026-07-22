# Troubleshooting

Common setup and runtime issues for **external users** of `stubborn-stub` and
sibling packages. For goal-oriented entry paths see
[stubborn-hub USER-JOURNEY](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md).

## Quick diagnostics

```bash
stubborn doctor
stubborn-status --json          # after: pip install stubborn-status
```

Doctors are **read-only** — they do not run scip-java, ingest, or migrate your
database ([ADR-015](adr/ADR-015-federated-doctor-diagnostics.md)).

```bash
stubborn-status --json --require stubborn-stub,stubborn-mcp   # MCP workflows
```

Full federated report across `stubborn-stub`, `stubborn-mcp`, `stubborn-watch`.
See [ADR-016](adr/ADR-016-doctor-status-aggregation.md).

---

## Which journey am I on?

| Your goal | Journey | First command |
|-----------|---------|---------------|
| Smoke test, no Java | [A](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md#journey-a--try-in-30-seconds-no-java) | `stubborn try` |
| Cursor / MCP agent | [B](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md#journey-b--cursor--mcp-agents) | `stubborn-mcp doctor` after `STUBBORN_DB` is set |
| Real Java / Spring repo | [C](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md#journey-c--real-java--spring-project) | `scip-java index` → `stubborn index` |
| Microservices + OpenAPI | [D](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md#journey-d--microservices--contract-graph) | `index-openapi` / `index-contract` |
| CI / release maintainer | [E](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/USER-JOURNEY.md#journey-e--ci-doctor-release-matrix) | `stubborn-status --json` |

`stubborn doctor` prints journey hints when `--fix-hint` is enabled (default).

---

## Installation and naming

### `pip install stubborn` does not work

PyPI package name is **`stubborn-stub`**. CLI command is **`stubborn`**.

```bash
pip install stubborn-stub
stubborn --help
```

### `stubborn-mcp` / `stubborn-watch` not found

Each surface is a **separate PyPI package**:

```bash
pip install stubborn-mcp
pip install stubborn-watch
```

### Which optional extra do I need?

| Input | Install |
|-------|---------|
| Bundled `--fixture minimal` or `.json` fixture | `stubborn-stub` only |
| Binary `.scip` or NDJSON from scip-java | `pip install "stubborn-stub[scip]"` |
| `stubborn index-openapi` with YAML specs | `pip install "stubborn-stub[openapi]"` or `[dev]` |

Error mentioning `protobuf` or SCIP binary decode → install **`[scip]`**.

---

## 30-second quickstart fails

### `examples/fixtures/minimal.json` not found

That path exists only in the **git repository**, not in the PyPI wheel.

Use a bundled fixture instead:

```bash
pip install stubborn-stub
stubborn try
```

Or manual steps:

```bash
stubborn index --fixture minimal --out /tmp/symbols.db
```

Or print the installed path:

```bash
stubborn fixture-path minimal
stubborn index --scip "$(stubborn fixture-path minimal)" --out /tmp/symbols.db
```

List bundled names: `stubborn fixtures`.

---

## Indexing

### `One of --scip or --fixture is required`

`stubborn index` needs either:

```bash
stubborn index --scip path/to/index.scip --out metadata/symbols.db
stubborn index --fixture minimal --out metadata/symbols.db
```

### scip-java / Maven errors (real projects)

Stubborn does not compile Java. You need a working toolchain **before** Stubborn:

1. `mvn -q package` (or your build) succeeds
2. `scip-java index --build-tool maven` produces `index.scip`
3. `stubborn index --scip index.scip --out metadata/symbols.db`
4. `stubborn doctor` — expect `db.present` pass; warnings about missing `[scip]` mean
   install `pip install "stubborn-stub[scip]"` for binary `.scip` (NDJSON/JSON may work without)

**Common failures:**

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `scip-java: command not found` | CLI not on PATH | [scip-java install](https://github.com/sourcegraph/scip-java#installation) (`cs install scip-java`); or reuse `index.scip` with `index-java-project.sh --no-build` |
| `index.scip` missing after index | Maven build failed | Fix `mvn package` first |
| `protobuf` / decode error on index | Missing `[scip]` extra | `pip install "stubborn-stub[scip]"` |
| Doctor: `index.scip` but no DB | Skipped `stubborn index` | Run step 3 above |

Validated reference: [`stubborn-demo/demo-spring`](https://github.com/stubborn-ai/stubborn-demo/tree/main/demo-spring).
For your own repo, use [`stubborn-demo/scripts/index-java-project.sh`](https://github.com/stubborn-ai/stubborn-demo/blob/main/scripts/index-java-project.sh).
Host launcher runs `stubborn-preflight.sh` before E2E (see [DEMO-LAUNCHERS](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md)).

### `--merge` / `--paths` errors

`--paths` requires `--merge`. See [ADR-009](adr/ADR-009-incremental-index-merge.md) and
`stubborn-watch` for the dev-loop story.

---

## Context and stable IDs

### `Target not found in index: ...`

The `stable_id` is wrong or from a different index run. Discover targets:

```bash
stubborn list-symbols metadata/symbols.db --query OrderService
stubborn list-symbols metadata/symbols.db --query VetController
```

Copy the first column (`stable_id`) into `--target` or MCP `get_context`.

SCIP ID format is verbose (e.g. `semanticdb maven com/example/OrderService#`).
That is normal.

### Empty or tiny context

- Try `--prune-mode strict` vs default `smart` ([ADR-003](adr/ADR-003-type-neighbor-pruning.md))
- Raise `--max-symbols` or `--call-depth` if the graph is deep
- Confirm the symbol exists: `stubborn info metadata/symbols.db`

---

## MCP (stubborn-mcp)

### Checklist before opening Cursor

1. **Indexed DB exists** — Journey A (`stubborn try`) or Journey C (`stubborn index`).
2. **`STUBBORN_DB` points at that file** — absolute or `${workspaceFolder}/metadata/symbols.db`.
3. **Same venv on PATH** — `which stubborn-mcp` matches where you `pip install`ed.
4. **Federated check:**

   ```bash
   export STUBBORN_DB=metadata/symbols.db
   stubborn-mcp doctor
   stubborn-status --json --require stubborn-stub,stubborn-mcp
   ```

### MCP server starts but tools return errors

1. Confirm `STUBBORN_DB` points at an existing file:

   ```bash
   export STUBBORN_DB=metadata/symbols.db
   stubborn-mcp doctor
   ```

2. Build the DB first (Journey A fixture or real `index.scip`).

3. For workspace queries, pass `workspace` consistently in tools and when indexing
   (`--workspace`, `--repo`).

### Cursor does not show Stubborn tools

- Check `.cursor/mcp.json` uses `stubborn-mcp` on `PATH` (same venv as install)
- Restart MCP / reload window after config changes
- Run `stubborn-mcp doctor --json` in the same environment Cursor uses

Smoke scripts: `stubborn-demo/demo-spring/scripts/mcp-smoke.sh` (requires prior E2E).

---

## Contract graph

### `list-contracts` is empty

Contract facts are **not** created by SCIP ingest alone. You need:

```bash
stubborn index-openapi --openapi <spec> --service <name> --workspace <ws> --out metadata/symbols.db
# and/or
stubborn index-contract --manifest <manifest> --out metadata/symbols.db
```

Reference manifest: [`stubborn-demo/.../contracts/http.yml`](https://github.com/stubborn-ai/stubborn-demo/tree/main/spring-petclinic-microservices/contracts).

### OpenAPI ingest validation errors

- `--service` is required
- Paths must be valid OpenAPI 3.x
- Use `--workspace` when composing multiple sources in one DB

---

## Database and schema

### Doctor warns about schema version

Doctors **do not** auto-migrate legacy DBs ([ADR-015](adr/ADR-015-federated-doctor-diagnostics.md)).
Re-index with the current `stubborn-stub` release:

```bash
stubborn index --scip index.scip --out metadata/symbols.db
```

Contract features need **schema v4** ([ADR-012](adr/ADR-012-schema-v4-contract-evidence.md)).

### `metadata/symbols.db` not found

Default discovery looks for `metadata/symbols.db` under the project root you pass
to `stubborn doctor`. Override:

```bash
stubborn doctor --db /path/to/symbols.db
stubborn-status --db /path/to/symbols.db
```

---

## Demos and Docker

### Host E2E script fails immediately

Check [DEMO-LAUNCHERS.md](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md):

- `mvn`, `scip-java`, `stubborn`, `python3` on `PATH`
- `dukesbank` needs `export BANK_ROOT=...`
- PetClinic demos clone upstream into local `upstream/` on first host run

Prefer Docker when the host toolchain is incomplete:

```bash
cd stubborn-demo
docker compose build
docker compose run --rm e2e
```

### Windows

Use **WSL2** for bash/Docker workflows. PowerShell launchers are fallback only.

---

## Version skew

Satellite packages pin a `stubborn-stub` range. If MCP fails with import errors,
upgrade together:

```bash
pip install -U stubborn-stub stubborn-mcp stubborn-watch stubborn-status
```

Canonical matrix: [stubborn-hub README](https://github.com/stubborn-ai/stubborn-hub#release-matrix).

---

## Still stuck?

1. `stubborn-status --json` — full federated report
2. Reproduce on the **bundled fixture** to isolate toolchain vs project issues
3. Compare with a **Docker E2E** tier from `stubborn-demo`
4. Open an issue with doctor JSON, command line, and `stubborn info` output (no secrets)
