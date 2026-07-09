# ADR-016: Doctor status aggregation (`stubborn-status`)

- **Status:** Accepted
- **Documented:** 2026-07-07
- **Deciders:** Stubborn maintainers
- **Related:** [ADR-015](ADR-015-federated-doctor-diagnostics.md) (federated per-package `doctor`)

## Context

[ADR-015](ADR-015-federated-doctor-diagnostics.md) assigns each ecosystem package its
own read-only `doctor` command and **rejects** a meta-doctor inside
**stubborn-stub** that shells out to every sibling CLI. That keeps the core
compiler free of “know how to call every package” coupling (ADR-006, ADR-008).

Users still need a **single view** of ecosystem health in several contexts:

| Consumer | Need |
|----------|------|
| **Terminal users** | One command for “is my Stubborn setup OK?” without memorizing four CLIs |
| **CI/CD** | One exit code + machine-readable report for workspace health gates |
| **IDE bridges** | `vscode-stubborn`, future IntelliJ extension — panel or notification summarizing setup |
| **Hub runbooks** | Documented entrypoint that is not IDE-specific |

Implementing aggregation inside **vscode-stubborn** alone would duplicate logic
when IntelliJ or CI needs the same behavior, and would blur IDE custody with
cross-package orchestration.

ADR-015 introduced `--json` output on each `doctor` partly to enable programmatic
consumption. Once multiple tools depend on merged reports, that JSON shape is no
longer an implementation detail — it becomes a **public contract** between
packages and any aggregator.

## Decision

### 1. Aggregation lives in a separate package/repo: `stubborn-status`

Charter a thin program repo (PyPI **`stubborn-status`**, CLI entry
**`stubborn-status`**) that:

1. **Discovers** installed ecosystem `doctor` commands (see registry below).
2. **Invokes each as an external subprocess** with `--json` (never `import`
   sibling package internals).
3. **Merges** results into one report while **preserving source package
   attribution** on every check.
4. **Exposes** the merged report as:
   - human-readable CLI output (default), and
   - `--json` for IDE bridges, CI, and scripts.

`stubborn-status` is **not** part of `stubborn-stub`, **not** part of
`vscode-stubborn`, and **not** a second meta-doctor hidden inside core. It is
the same architectural pattern as `stubborn-mcp` (protocol adapter) and
`stubborn-watch` (orchestration glue): a **small dedicated repo** for a
capability multiple consumers need.

### 2. What `stubborn-status` may and may not do

| Allowed | Forbidden |
|---------|-----------|
| `subprocess` each registered `doctor --json` | Import `stubborn_mcp`, `stubborn_watch`, etc. |
| Skip or mark **not installed** when a CLI is absent | Fail the whole run because one optional package is missing |
| Compute aggregate exit code from child exits | Run ingest, index, scip-java, or start MCP |
| Print delegation hints with **package name** on each check | Collapse checks into anonymous “setup OK” without source |
| Read project cwd for shared `PATH` / cwd context passed to children | Guess OpenAPI `service` / `workspace` / auto-select index source |

Graceful degradation is required: if `stubborn-watch` is not installed, the
merged report includes a `not_installed` (or equivalent) section for that
package — not silence, not a crash.

### 3. Doctor registry (initial)

`stubborn-status` maintains a **static registry** of known doctors (versioned
with the aggregator). Initial entries:

| Package | Command | Required? |
|---------|---------|-----------|
| `stubborn-stub` | `stubborn doctor` | **Yes** — always attempted |
| `stubborn-mcp` | `stubborn-mcp doctor` | No — optional unless `--require mcp` |
| `stubborn-watch` | `stubborn-watch doctor` | No |
| `stubborn-indexer` | `stubborn-indexer doctor` | No — future |

IDE-specific checks (editor settings, extension activation) remain in
**vscode-stubborn** / future IntelliJ repos. Those IDEs **consume**
`stubborn-status --json`; they do not reimplement merge logic.

### 4. Public JSON contracts

#### 4a. Per-package report (`doctor --json`)

Each federated `doctor` **must** emit JSON conforming to **Doctor Report v1**
when `--json` is set:

```json
{
  "schema": "stubborn.doctor-report/v1",
  "package": "stubborn-stub",
  "command": "stubborn doctor",
  "version": "0.9.0b5",
  "cwd": "/path/to/project",
  "exit": 0,
  "checks": [
    {
      "id": "core.import",
      "status": "pass",
      "message": "stubborn-stub importable",
      "hint": null
    }
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `schema` | yes | Constant `stubborn.doctor-report/v1` |
| `package` | yes | PyPI / program package id (e.g. `stubborn-mcp`) |
| `command` | yes | argv shape invoked |
| `version` | yes | Installed package version string |
| `cwd` | yes | Working directory used for the run |
| `exit` | yes | This doctor’s exit code (0 / 1 / 2 per ADR-015) |
| `checks` | yes | Array (may be empty) |
| `checks[].id` | yes | Stable dot-separated id within package |
| `checks[].status` | yes | `pass` \| `warn` \| `fail` \| `skip` \| `info` |
| `checks[].message` | yes | Human-readable summary |
| `checks[].hint` | no | Copy-paste fix; must name owning package in text |

**Compatibility:** additive fields are allowed in minor releases; removing or
renaming fields requires a new schema version (`v2`). Aggregator and IDEs must
ignore unknown fields.

#### 4b. Aggregated report (`stubborn-status --json`)

```json
{
  "schema": "stubborn.status-report/v1",
  "aggregator": "stubborn-status",
  "version": "0.1.0b1",
  "cwd": "/path/to/project",
  "exit": 1,
  "doctors": [
    {
      "package": "stubborn-stub",
      "state": "ran",
      "report": { }
    },
    {
      "package": "stubborn-watch",
      "state": "not_installed",
      "report": null
    }
  ]
}
```

| `doctors[].state` | Meaning |
|-------------------|---------|
| `ran` | Subprocess completed; `report` is Doctor Report v1 |
| `not_installed` | CLI not on PATH |
| `skipped` | Excluded by flags (e.g. `--only core`) |
| `failed_to_run` | Subprocess error (timeout, non-JSON stdout) |

**Aggregate exit code:**

- `1` if any **required** doctor has `exit === 1` or `state === failed_to_run`
- `2` if no blocking failures but any child `exit === 2` or `warn` checks exist
- `0` otherwise

Required doctors default to `stubborn-stub` only; `--require mcp,watch` opts in.

### 5. Consumer rules (IDE, CI, terminal)

All consumers **should** call `stubborn-status` (or parse its `--json`) rather
than reimplementing merge logic:

| Consumer | Integration |
|----------|-------------|
| Terminal | `stubborn-status` or `stubborn-status --json` |
| CI | `stubborn-status --json --require stubborn-stub` with exit code gate |
| vscode-stubborn | Run `stubborn-status --json` in extension host; render panel **after** sidecar stub MVP |
| Future IntelliJ | Same subprocess contract |

vscode-stubborn **must not** import Python modules from other Stubborn packages
for doctor aggregation. TypeScript may only spawn CLI processes — same coupling
model as ADR-015 allows for `stubborn-watch` → `scip-java`.

### 6. Amend ADR-015 (cross-reference only)

ADR-015’s `vscode-stubborn` row is **IDE settings and sidecar UX only** — not
doctor aggregation. Aggregation custody moves to **`stubborn-status`** per this
ADR. ADR-015’s rejection of “meta-doctor in core” remains unchanged.

## Consequences

### Positive

- One implementation of merge logic for terminal, CI, and all IDE bridges
- ADR-015 federated model stays intact; friction drops without core bloat
- JSON schemas are explicit compatibility surfaces for programmatic consumers
- Optional packages degrade cleanly

### Negative / trade-offs

- Another repo to maintain (acceptable per existing `stubborn-*` pattern)
- Registry must be updated when new `doctor` packages ship
- Subprocess overhead vs in-process (acceptable for diagnostic frequency)
- Schema stability obligation — changes need version discipline

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Aggregation only in vscode-stubborn** | Not reusable for CI, terminal, IntelliJ; duplicates merge logic |
| **Meta-doctor in stubborn-stub** | Rejected in ADR-015; core coupling |
| **Hub shell script only** | No PyPI discoverability; IDEs still reimplement parsing |
| **Each IDE parses all `doctor --json` itself** | N× merge implementations; schema drift risk |
| **Single JSON file on disk updated by doctors** | Racey, stale state, no clear ownership |

## Implementation notes (non-normative)

**Status (2026-07):**

1. ✅ Per-package `doctor --json` (Doctor Report v1) per ADR-015 — `stubborn`,
   `stubborn-mcp`, `stubborn-watch`
2. ✅ [`stubborn-status`](https://github.com/stubborn-ai/stubborn-status) repo
   **`0.1.0b1`** on [PyPI](https://pypi.org/project/stubborn-status/) — registry, subprocess merge, tests
3. ✅ Documented in hub [DEMO-LAUNCHERS](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md) setup checklist
4. 📋 vscode-stubborn doctor panel **after** sidecar stub path works — consumes
   `stubborn-status --json`

Normative schema files may later live in `stubborn-hub/schemas/` or `stubborn/docs/schemas/`; this ADR is the initial spec.

## References

- [ADR-015](ADR-015-federated-doctor-diagnostics.md) — federated doctor
- [ADR-006](ADR-006-mcp-first-agent-integration.md) — adapter repo pattern
- [ADR-008](ADR-008-weak-coupling-ecosystem.md) — weak coupling
- [stubborn-hub ECOSYSTEM](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/ECOSYSTEM.md)
- [stubborn-hub DEMO-LAUNCHERS](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/DEMO-LAUNCHERS.md)
