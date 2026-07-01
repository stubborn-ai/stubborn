# Docker environment

Reproducible toolchain for Stubborn without installing JDK, Maven, or scip-java locally.

## Image contents

| Tool | Version |
|------|---------|
| JDK | Eclipse Temurin 21 |
| Maven | distro package (Noble) |
| scip-java | `0.12.3` (`scip-java_2.13`, via Coursier) |
| Python | 3.x + `stubborn` editable install |

## Quick start

From the **repository root**:

```bash
# Build image
docker compose build

# Run demo-spring E2E (writes artifacts to examples/demo-spring/metadata/)
docker compose run --rm e2e

# Run spring-petclinic scale-up E2E (~5 min first run; clones upstream)
docker compose run --rm petclinic-e2e

# Duke's Bank Step 7 (requires sibling dukesbank clone at ../../dukesbank)
docker compose run --rm dukesbank-e2e

# Inspect outputs on the host
ls examples/demo-spring/metadata/
cat examples/demo-spring/metadata/order-service.stub.java

# Stubborn-DSL (after indexing):
docker compose run --rm cli context /demo/metadata/symbols.db \
  --target "<stable_id>" --format stubborn-dsl
```

See [docs/STUBBORN-DSL.md](../docs/STUBBORN-DSL.md).

## Services

| Service | Purpose |
|---------|---------|
| `e2e` | Runs `docker/run-e2e.sh` on mounted `examples/demo-spring` |
| `petclinic-e2e` | Clones pinned spring-petclinic, full scale-up pipeline |
| `shell` | Interactive bash with full toolchain |
| `cli` | Run arbitrary `stubborn` commands |

### Interactive shell

```bash
docker compose run --rm shell
# inside container:
cd /demo && mvn -q -DskipTests package
scip-java index
stubborn index --scip index.scip --out metadata/symbols.db
```

### One-off CLI

```bash
docker compose run --rm cli info /demo/metadata/symbols.db
```

Mount your own project by editing `docker-compose.yml` or:

```bash
docker compose run --rm \
  -v /path/to/your/java/project:/demo \
  e2e
```

## Build arguments

```bash
docker compose build --build-arg SCIP_JAVA_VERSION=0.12.3
```

## Windows notes

- Use Docker Desktop with Linux containers.
- Generated files appear under `examples\demo-spring\metadata\` via bind mount.
- PowerShell users can still use `examples/demo-spring/scripts/run-e2e.ps1` on the host.

## Related

- [examples/demo-spring/README.md](../examples/demo-spring/README.md) — demo app and cases
- [examples/spring-petclinic/README.md](../examples/spring-petclinic/README.md) — scale-up E2E
- [docs/SCIP-INGEST.md](../docs/SCIP-INGEST.md) — SCIP ingest details
