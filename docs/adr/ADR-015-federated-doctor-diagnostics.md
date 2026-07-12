# ADR-015: Federated `doctor` diagnostics per package

- **Status:** Accepted
- **Documented:** 2026-07-07
- **Deciders:** Stubborn maintainers

## Context

Onboarding friction is real: users must produce or obtain a SCIP index, understand
when a workspace is required, wire MCP, and install the right PyPI extras. A
common product response is a single “zero config” entrypoint that auto-detects
project type, invokes external indexers, and picks the “best” index source.

That response conflicts with decisions already in effect:

- **ADR-001** — SCIP is the code-symbol machine index; Stubborn does not parse
  source or invoke indexers from the core compiler.
- **ADR-006** — MCP ships in **stubborn-mcp**; the core owns `stubborn.api` only.
- **ADR-008** — weak coupling between repos; no monolithic “god CLI” that owns
  every integration surface.
- **ADR-011 / ADR-012** — contract facts are evidence-tiered; the system must
  not silently choose SCIP vs OpenAPI or upgrade evidence on the user’s behalf.
- **ADR-014** — optional capabilities (e.g. binary SCIP) are explicit extras,
  not assumed defaults.

A single `stubborn doctor` that checks scip-java, Cursor MCP JSON, watch
configs, and Docker toolchains would either **bloat the core** with orchestration
responsibilities reserved for sibling packages, or **over-promise** health checks
it cannot maintain as those packages evolve independently.

We still need a first-class onboarding path. The maintainers agree that
**diagnostics are valuable** when they are **scoped, honest, and federated** —
each package reports on what it owns, and program docs show how to run the set.

## Decision

Introduce a **`doctor` subcommand in each ecosystem package** that owns a slice
of the setup path. There is **no unified meta-doctor in `stubborn-stub`** that
executes or impersonates sibling checks.

### Package ownership

| Package / repo | Command | Custody (what it may diagnose) |
|----------------|---------|--------------------------------|
| **stubborn-stub** (`stubborn`) | `stubborn doctor` | Core install & optional `[scip]` extra; read-only `symbols.db` health (`info`, schema version, workspace repo summaries, contract binding **counts/tiers**); passive project **signals** (e.g. `pom.xml`, `openapi.yaml`, `.stubborn.toml` if present); copy-paste **explicit** next `stubborn …` commands. |
| **stubborn-mcp** | `stubborn-mcp doctor` | `STUBBORN_DB` / configured `db_path`; DB readable by `stubborn.api`; minimal tool surface smoke (`workspace_info` or equivalent); `.cursor/mcp.json` shape **when present** (parse only, no IDE RPC). |
| **stubborn-watch** | `stubborn-watch doctor` | Watch root, debounce, target DB, indexer command on `PATH`, merge prerequisites; workspace manifest when used. |
| **stubborn-indexer** (future repo) | `stubborn-indexer doctor` | scip-java / scip-* on `PATH`, versions, Maven/Gradle signals, suggested **user-run** index commands. **Not** implemented in core. |
| **stubborn-status** ([stubborn-status](https://github.com/stubborn-ai/stubborn-status)) | `stubborn-status` | Aggregate federated `doctor --json` reports via subprocess; terminal, CI, and IDE consumers. See [ADR-016](ADR-016-doctor-status-aggregation.md). **Beta** [`0.10.0b1` on PyPI](https://pypi.org/project/stubborn-status/). |
| **vscode-stubborn** (planned) | extension commands | Editor settings, MCP sidecar registration, **consumes** `stubborn-status --json` for setup panels — does not own merge logic. |

Packages **must not** diagnose another package’s custody in depth. They may
**delegate with a one-line hint**, e.g. “Run `stubborn-mcp doctor` for MCP
setup,” without importing sibling code or shelling out to sibling CLIs by default.

### Shared protocol (all `doctor` commands)

1. **Read-only by default** — no ingest, merge, index, MCP server start, or
   **schema migration** on `symbols.db` (inspect legacy schema versions; warn
   rather than upgrade in place).
2. **No auto-orchestration** — do not invoke `scip-java`, `mvn`, `gradle`, or
   `stubborn index` on the user’s behalf.
3. **No source selection** — if multiple index sources exist, list them and
   show **separate explicit commands**; never pick “best.”
4. **No guessing contract identity** — do not infer OpenAPI `service` /
   `workspace` / `version` (ADR-011).
5. **Exit codes** (consistent across packages):
   - `0` — ready, or only informational notes
   - `1` — blocking issue (missing package, unreadable DB)
   - `2` — non-blocking warnings (e.g. missing `[scip]` while only JSON
     fixtures exist; **legacy schema below current** — re-index recommended)
6. **Output** — human-readable sections by default; optional `--json` conforming
   to **Doctor Report v1** (see [ADR-016](ADR-016-doctor-status-aggregation.md)).
7. **Hints** — `--fix-hint` (default on) may print copy-paste commands; each
   hint must state **which package** owns the action.

### What `stubborn doctor` explicitly does not do

- Invoke or version-check **scip-java** (→ future `stubborn-indexer doctor`)
- Validate **MCP stdio** or Cursor connectivity (→ `stubborn-mcp doctor`)
- Validate **file-watch / merge loop** (→ `stubborn-watch doctor`)
- Create a default workspace for single-repo users (legacy single-DB mode
  remains sufficient; ADR-010 workspace is opt-in for multi-repo)
- Replace E2E proofs in **stubborn-demo**

### Program documentation

**stubborn-hub** documents the recommended order (not a new executable):

```bash
stubborn doctor
stubborn-indexer doctor    # when SCIP index is missing (future)
stubborn-watch doctor      # when using dev watch loop
stubborn-mcp doctor        # when using agents / Cursor
```

Link from [START-HERE.md](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/START-HERE.md) and
[DEMO-LAUNCHERS.md](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md).

### Relationship to “frictionless onboarding”

`doctor` is the **approved** onboarding mechanism for the beta era:

- **Diagnose and guide** with explicit next steps
- **Defer automation** to future, separately versioned packages (`stubborn-indexer`, IDE bridges)
- **Reject** “mixed mode auto-select best source” as a product feature

Future `.stubborn.toml` (project config) is **out of scope for this ADR**; if
added, it requires its own ADR defining precedence vs CLI flags and env vars.

## Consequences

### Positive

- Preserves ADR-006 / ADR-008 repo boundaries while improving DX
- Each team can ship and test its diagnostics beside its features
- Users get honest scope: `stubborn doctor` means “is my graph usable?” not
  “is my entire IDE stack perfect?”
- Aligns with evidence-tier honesty (ADR-011/012): doctors report tiers, they
  do not upgrade them

### Negative / trade-offs

- Multiple commands to learn; mitigated by hub “setup checklist” doc
- Risk of duplicated filesystem scanning (core and indexer both see `pom.xml`);
  acceptable if messages differ by custody
- No single exit code for “whole program healthy”; use
  [stubborn-status](ADR-016-doctor-status-aggregation.md) or call doctors
  explicitly in CI
- Sibling packages must implement `doctor` to stay symmetric; lag in one package
  leaves a gap in the checklist

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Monolithic `stubborn doctor` in core** | Violates ADR-001/008; core would own MCP, scip-java, and IDE checks |
| **`stubborn init` / `quickstart` with auto index** | Orchestration belongs in `stubborn-indexer` or demo templates, not core; auto-ingest conflicts with explicit evidence (ADR-011/012) |
| **Hub-only shell script** | Useful as doc, but not discoverable from `stubborn --help`; packages still need owned diagnostics |
| **Meta-doctor that shells out to all siblings** | Hidden coupling in **core**; rejected — aggregation belongs in **stubborn-status** ([ADR-016](ADR-016-doctor-status-aggregation.md)), not `stubborn-stub` |
| **No doctor; docs only** | Friction remains; misses low-risk, testable onboarding win |

## Implementation notes (non-normative)

**Status (2026-07):** items 1–3 below are **shipped** in beta repos. Item 4
(`stubborn-indexer`) remains future.

Ship order (completed unless noted):

1. ✅ `stubborn doctor` — DB + core package + passive signals (read-only inspect;
   `read_info(..., migrate=False)`)
2. ✅ `stubborn-mcp doctor` — MCP surface and config shape
3. ✅ `stubborn-watch doctor` — dev-loop prerequisites
4. `stubborn-indexer doctor` — when that repo is chartered (ADR for indexer
   boundary may precede or follow; this ADR does not create the repo)

Core implementation lives under `src/stubborn/doctor/` with unit tests on
fixture DBs, legacy-schema regression tests, and temp project trees. MCP/watch
mirror the same report schema.

## References

- [ADR-001](ADR-001-scip-as-machine-index.md) — SCIP boundary
- [ADR-006](ADR-006-mcp-first-agent-integration.md) — MCP package split
- [ADR-008](ADR-008-weak-coupling-ecosystem.md) — multi-repo weak coupling
- [ADR-011](ADR-011-openapi-contract-graph.md) — explicit contract authority
- [ADR-012](ADR-012-schema-v4-contract-evidence.md) — evidence tiers
- [stubborn-hub DEMO-LAUNCHERS](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md)
- [stubborn-hub PETCLINIC-VALIDATION](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/PETCLINIC-VALIDATION.md)
- [ADR-016](ADR-016-doctor-status-aggregation.md) — doctor status aggregation
