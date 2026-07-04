# Examples

Core fixtures for Stubborn unit and contract tests.

Runnable demos and black-box validation projects live in
[`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo). This keeps the
core repo focused on headless ingest, store, prune, weave, API, and CLI
behavior, without mirrored demo copies that can drift.

## Recommended workflow

- **Docker-first** for reproducible demo and validation runs
- **WSL2** on Windows when you want a bash-compatible shell locally
- **PowerShell** only for host-side fallback scripts when you need them

| Path | Status | Description |
|------|--------|-------------|
| [fixtures](fixtures/) | Active | Minimal JSON / binary SCIP fixtures for tests and quick starts |

## Recommended Demo Path

Use `stubborn-demo` for product demos and validation:

```bash
git clone https://github.com/stubborn-ai/stubborn-demo
cd stubborn-demo
docker compose build
docker compose run --rm e2e
```

If you are on Windows and prefer a bash-compatible shell, use WSL2 and the same Docker
commands. If you need a host fallback, the demo repositories still keep PS1
wrappers.

## Documentation

- [docs/README.md](../docs/README.md) — full doc index
- [stubborn-demo](https://github.com/stubborn-ai/stubborn-demo) — runnable demos and validation
