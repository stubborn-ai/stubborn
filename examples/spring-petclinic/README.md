# Spring PetClinic — scale-up E2E

Official [spring-petclinic](https://github.com/spring-projects/spring-petclinic) indexed via **scip-java** + Stubborn. Validates compression and neighbor coverage on a ~30-file Spring Boot app (vs ~14 in demo-spring).

| | demo-spring | spring-petclinic |
|---|-------------|------------------|
| Java files | ~14 | ~30 (`src/main/java`) |
| Index symbols | ~92 | **~375** |
| VetController stub | ~450 tokens | **~1,426 tokens** |
| Token savings | ~81% | **~90%** |
| CI | every PR (light) | weekly / manual |

## Quick start (Docker)

From repo root:

```bash
docker compose build stubborn
docker compose run --rm petclinic-e2e
```

Clones upstream (pinned in [`upstream.pin`](upstream.pin)), runs Maven + `scip-java index --build-tool maven`, indexes SQLite, emits `VetController` context, runs verify guard.

Outputs (gitignored locally):

- `metadata/symbols.db`
- `metadata/vet-controller.stub.java`

## Host E2E (PowerShell)

Requires JDK 21+, Maven, scip-java, stubborn on PATH.

```powershell
cd examples/spring-petclinic
./scripts/run-e2e.ps1
```

Clones to `upstream/` (gitignored).

## Cases

| Case | Target | Doc |
|------|--------|-----|
| vet-controller | `VetController` | [cases/vet-controller-context.md](cases/vet-controller-context.md) |

## Pin

Upstream commit is pinned in [`upstream.pin`](upstream.pin). Bump intentionally after validating a new PetClinic release.

## CI

[`.github/workflows/petclinic-e2e.yml`](../../.github/workflows/petclinic-e2e.yml) — `workflow_dispatch` + weekly schedule (not on every PR).

## Related

- [demo-spring](../demo-spring/) — fast day-to-day regression
- [docker/README.md](../../docker/README.md) — toolchain image
