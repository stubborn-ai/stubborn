# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.10.0b1] - 2026-07-12

### Changed

- Align program-wide PyPI version line to **0.10.0b1** (unified release matrix across core and satellite packages).

## [0.9.0b7] - 2026-07-12

### Added

- **`stubborn try`** — one-command bundled-fixture demo (`index` → `list-symbols` → `context` on stdout).

## [0.9.0b6] - 2026-07-12

### Added

- **Bundled fixtures** — `stubborn fixtures`, `stubborn fixture-path`, and `stubborn index --fixture minimal` for pip-install quickstart without cloning the git repo.
- **`stubborn doctor`** — read-only setup diagnostics per [ADR-015](docs/adr/ADR-015-federated-doctor-diagnostics.md) (`--json`, Doctor Report v1).
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — common external-user setup failures and fixes.

### Fixed

- **`stubborn doctor`** no longer migrates legacy `symbols.db` schema during inspection (`read_info(..., migrate=False)`).

## [0.9.0b5] - 2026-07-04

### Added

- **ADR-011/012 contract graph** — explicit OpenAPI contract ingest, schema v4 contract evidence tables, and `index-contract` for manifest-based contract evidence.
- **ADR-013 source-neutral queries** — `prune_context` and workspace summaries now treat code and contract sources as peers, with `contract_endpoint` targets, `contract_endpoints` graph facts, and `list_contracts` discovery.
- **ADR-014 optional SCIP runtime** — `protobuf` moved behind the `scip` extra, while core/API/JSON-fixture paths remain importable without the SCIP runtime.

### Changed

- `stubborn index-openapi` supports contract-only workspaces without code bindings; `stubborn-dsl` renders endpoint/schema facts under `contracts:`.
- `stubborn info --workspace` now reports code repos and contract sources separately.
- Core docs and examples now describe code/contract source kinds as peers.

### Fixed

- Deduplicated SCIP enrichment logic so the pure enrichment path and protobuf ingest share one implementation.

## [0.9.0b4] - 2026-07-03

### Added

- Architecture Decision Records (`docs/adr/`) — ADR-001 through ADR-009.
- [ADR-009](docs/adr/ADR-009-incremental-index-merge.md) — incremental `--merge` vs full snapshot indexing.
- [DEVELOPMENT-MODEL.md](docs/DEVELOPMENT-MODEL.md) — architecture-led, AI-assisted engineering declaration.
- **`--prune-mode`** (`smart` | `strict` | `fast`) on `context`, `metrics`, and API — user control over neighbor expansion.
- Ingest signature enrichment edges tagged as `signature-ref` (skipped in `strict` / `fast`).

### Changed

- **MCP moved to [stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)** — removed `stubborn.mcp_server`, `[mcp]` extra, `stubborn mcp` CLI; use `pip install stubborn-mcp`.
- Renamed store read model `SymbolRecord` → `SymbolSummary` (distinct from ingest `SymbolRecord`).
- `list_symbols` API now includes `documentation` in results.
- [POSITIONING.md](docs/POSITIONING.md) — primary/secondary audience, honest competitor comparison, SCIP prerequisite, language scope.
- [README.md](README.md) — three-axis comparison (not RAG-only); dual use cases; requirements table.
- [BETA.md](docs/BETA.md) — audience fit, expanded limitations, out-of-scope for zero-config indexing.
- [examples/README.md](examples/README.md) — Java-only validated examples note.

### Fixed

- **`signature-ref` edges silently dropped on ingest** — schema CHECK omitted `signature-ref`; `INSERT OR IGNORE` swallowed constraint failures. Schema updated; writer uses `INSERT … ON CONFLICT DO NOTHING`; regression test in `test_store.py`.
- **ADR fabricated retroactive dates** — replaced with `Documented: 2026-07-02` and README disclaimer.

## [0.9.0b3] - 2026-07-02

### Changed

- Finish standalone rename cleanup: remove legacy `anchor_stubborn` package, duplicate ANCHOR-DSL docs, and duplicate tests.
- Rename remaining test functions from `anchor_dsl` to `stubborn_dsl`.
- Update LICENSE copyright to "Stubborn contributors".
- Add ruff lint/format checks to CI.
- Add CLI smoke tests and a no-Java quick start in README.

### Fixed

- CI verify steps run on the host after Docker E2E (avoids `shell` entrypoint exit 126).

## [0.9.0b2] - 2026-07-01

### Changed

- Phase 2 rename: package `stubborn`, PyPI name `stubborn-stub`, format `stubborn-dsl`, env `STUBBORN_DB`.
- Polish standalone branding; de-emphasize anchor-migration in README.
- Beta classifier on PyPI.

### Fixed

- PyPI wheel duplicate schema file.
- Release workflow uses twine + `PYPI_API_TOKEN`.

## [0.9.0b1] / prior

See [GitHub Releases](https://github.com/stubborn-ai/stubborn/releases) for earlier tags and migration history.

[0.10.0b1]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b7...v0.10.0b1
[0.9.0b7]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b6...v0.9.0b7
[0.9.0b6]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b5...v0.9.0b6
[0.9.0b5]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b4...v0.9.0b5
[0.9.0b4]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b3...v0.9.0b4
[0.9.0b3]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b2...v0.9.0b3
[0.9.0b2]: https://github.com/stubborn-ai/stubborn/releases/tag/v0.9.0b2
