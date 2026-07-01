# Duke's Bank — stubborn E2E

Indexes the **external** [Duke's Bank](https://github.com/jiananwang/dukesbank) bank module via `scip-java` and emits LLM context for migration tasks (e.g. `AccountControllerBean` → Spring service).

This is the **formal runbook** for Duke's Bank LLM context. See also [migration-bridge](../migration-bridge/) and [INTEGRATION.md](../../docs/INTEGRATION.md).

## Layout contract

```
github/   (or C:\github\)
├── stubborn-ai/stubborn/examples/dukesbank/   ← this folder (metadata output only)
└── dukesbank/
    └── src/j2eetutorial14/examples/bank/     ← Java sources indexed by scip-java
```

Optional cross-program runbook: [anchor-migration/demo-dukesbank](https://github.com/anchor-migration/demo-dukesbank) Step 7.

## Quick start (host)

Requires JDK, Maven, `scip-java`, and `stubborn` on PATH:

```powershell
cd examples\dukesbank
.\scripts\run-e2e.ps1
python ..\..\scripts\verify_dukesbank_context.py
```

## Docker

From `stubborn` repo root (mounts sibling `dukesbank` at `/bank`):

```bash
docker compose build
docker compose run --rm dukesbank-e2e
```

Set `DUKESBANK_ROOT` if the bank module is not at `../../dukesbank/...` relative to this repo.

## Artifacts

| Path | Role |
|------|------|
| `metadata/symbols.db` | SCIP symbol graph (gitignored) |
| `metadata/account-controller.stub.java` | Default `java-stub` context |
| `metadata/account-controller.stubborn-dsl` | Optional compact graph |

## Program integration

- [INTEGRATION.md](../../docs/INTEGRATION.md) — optional anchor-migration program integration
