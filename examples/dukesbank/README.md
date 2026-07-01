# Duke's Bank — stubborn E2E

Indexes the **external** [Duke's Bank](https://github.com/jiananwang/dukesbank) bank module via `scip-java` and emits LLM context for migration tasks (e.g. `AccountControllerBean` → Spring service).

This is the **formal runbook** companion to [migration-bridge](../migration-bridge/) and [migration-hub DUKESBANK-DEMO Step 7](https://github.com/anchor-migration/migration-hub/blob/main/docs/DUKESBANK-DEMO.md#step-7--llm-context-stubborn).

## Layout contract

```
github/   (or C:\github\)
├── stubborn-ai/stubborn/examples/dukesbank/   ← this folder (metadata output only)
├── anchor-migration/demo-dukesbank/scripts/run-stubborn-context.ps1
└── dukesbank/
    └── src/j2eetutorial14/examples/bank/     ← Java sources indexed by scip-java
```

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

- [ADR-010](https://github.com/anchor-migration/migration-hub/blob/main/docs/ADR-010-anchor-stubborn-integration.md) — horizontal LLM context
- [demo-dukesbank runbook](https://github.com/anchor-migration/demo-dukesbank#optional--llm-context-stubborn) — optional Step 7 after SSOT E2E
