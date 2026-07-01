# Case: account-controller-context (Duke's Bank)

## Goal

Verify pruning from `AccountControllerBean` (EJB session facade) includes account, customer, and util types but excludes method bodies.

Typical migration task: Session→Service or CMP→JPA recipe design for the account controller.

## Prerequisites

External [Duke's Bank](https://github.com/jiananwang/dukesbank) clone as **sibling** of `anchor-migration`:

```
github/
├── stubborn-ai/stubborn/
└── dukesbank/src/j2eetutorial14/examples/bank/
```

## Command

```bash
# From bank module (host or Docker — see scripts/run-e2e.ps1)
cd dukesbank/src/j2eetutorial14/examples/bank
mvn -q -DskipTests package
scip-java index
anchor-stubborn index --scip index.scip --out /path/to/metadata/symbols.db

anchor-stubborn context metadata/symbols.db \
  --target "<AccountControllerBean stable_id>" \
  --out metadata/account-controller.stub.java

# Mapping / scoping (fewer tokens, graph-first):
anchor-stubborn context metadata/symbols.db \
  --target "<AccountControllerBean stable_id>" \
  --format anchor-dsl \
  --member-signatures neighbors \
  --javadoc summary \
  --out metadata/account-controller.anchor-dsl

anchor-stubborn metrics metadata/symbols.db \
  --target "<AccountControllerBean stable_id>" \
  --sources src
```

Docker (from `anchor-stubborn` repo root):

```bash
docker compose build
docker compose run --rm dukesbank-e2e
python scripts/verify_dukesbank_context.py
```

## Expected neighbors

Types in the pruned graph should include:

- `AccountControllerBean` (target)
- `LocalAccount` / `LocalAccountHome` (account CMP)
- `LocalCustomer` / `LocalCustomerHome`
- `LocalNextId` / `LocalNextIdHome`
- `AccountDetails`
- `SessionBean` (EJB contract)

## Weave recommendations

| Task | Flags |
|------|-------|
| Recipe / mapping draft | `--format anchor-dsl --member-signatures neighbors --javadoc summary` |
| Java codegen on controller | `--format java-stub --member-signatures target` |
| Minimum tokens | `--member-signatures off --javadoc off` |

## Baseline KPI

Run `docker compose run --rm dukesbank-e2e` or `scripts/run-e2e.ps1`, then read `metrics` output.

Target: **≥70%** token savings vs full `src/` tree (legacy EJB module is larger than demo-spring).

## Notes

- Bank module uses Maven (`pom.xml`) for `scip-java` indexing; Ant `build.xml` remains for legacy deploy.
- Stable id encoding varies by SCIP/Maven coordinates — E2E scripts resolve by `display_name`.
- This case is **horizontal** to SSOT → rewrite → parity (Steps 1–6 in [DUKESBANK-DEMO](https://github.com/anchor-migration/migration-hub/blob/main/docs/DUKESBANK-DEMO.md)).
