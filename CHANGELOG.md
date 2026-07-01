# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Architecture Decision Records (`docs/adr/`) — ADR-001 through ADR-008.
- [DEVELOPMENT-MODEL.md](docs/DEVELOPMENT-MODEL.md) — architecture-led, AI-assisted engineering declaration.
- **`--prune-mode`** (`smart` | `strict` | `fast`) on `context`, `metrics`, API, and MCP — user control over neighbor expansion.
- Ingest signature enrichment edges tagged as `signature-ref` (skipped in `strict` / `fast`).

### Changed

- Renamed store read model `SymbolRecord` → `SymbolSummary` (distinct from ingest `SymbolRecord`).
- `list_symbols` / MCP `list_symbols` now include `documentation` in results.
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

[0.9.0b3]: https://github.com/stubborn-ai/stubborn/compare/v0.9.0b2...v0.9.0b3
[0.9.0b2]: https://github.com/stubborn-ai/stubborn/releases/tag/v0.9.0b2
