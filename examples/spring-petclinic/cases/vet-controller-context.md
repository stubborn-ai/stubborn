# Case: vet-controller-context

## Goal

Validate scale-up E2E on the official [spring-petclinic](https://github.com/spring-projects/spring-petclinic) repo: richer graph, cross-package pruning, compression KPI.

## Command

```bash
# Docker (recommended)
docker compose run --rm petclinic-e2e

# Or after host E2E
stubborn context examples/spring-petclinic/metadata/symbols.db \
  --target "<VetController stable_id>" \
  --out examples/spring-petclinic/metadata/vet-controller.stub.java

# Optional: stubborn-dsl
stubborn context examples/spring-petclinic/metadata/symbols.db \
  --target "<VetController stable_id>" \
  --format stubborn-dsl \
  --out examples/spring-petclinic/metadata/vet-controller.stubborn-dsl
```

## Expected neighbors

Types in the pruned graph should include:

- `VetController` (target)
- `VetRepository` / `Vet`
- `Specialty`, `Vets`
- Related domain entities via JPA inheritance (`BaseEntity`, `Person`, …)

Modern PetClinic uses `VetRepository` directly (no `ClinicService` facade).

## Baseline KPI (pinned upstream, Docker E2E)

Pin: `examples/spring-petclinic/upstream.pin` (`b3ee2c53…`, 2026-06)

| Metric | Value |
|--------|-------|
| `source_files` | 30 |
| `source_tokens_est` | 14,479 |
| `index_symbols` | 375 |
| `stub_symbols` | 13 |
| `stub_tokens_est` | 1,426 |
| `compression_ratio` | **90.15%** |
| `token_savings` | **90.2%** |

Passes the ≥70% compression floor for scale-up guard.

## Notes

- `scip-java index --build-tool maven` required (repo ships both Maven and Gradle).
- Full index takes ~3–5 minutes (Maven + SCIP) on first Docker run.
- CI: weekly / manual workflow — not on every PR.
