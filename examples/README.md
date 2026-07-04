# Examples

Core fixtures for Stubborn unit and contract tests.

Runnable demos and black-box validation projects live in
[`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo). This keeps the
core repo focused on headless ingest, store, prune, weave, API, and CLI
behavior, without mirrored demo copies that can drift.

## Recommended workflow

- **Docker-first** for reproducible demo and validation runs
- **WSL2** on Windows when you want a bash-compatible shell locally
- **PowerShell** only as a fallback tier for Windows host users

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
commands. If you need a Windows host fallback, use the historical PS1 scripts from git
history or thin wrappers that forward to the same targets.

## Documentation

- [docs/README.md](../docs/README.md) — full doc index
- [stubborn-demo](https://github.com/stubborn-ai/stubborn-demo) — runnable demos and validation
