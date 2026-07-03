# Docker environment

Reproducible core CLI/toolchain image for Stubborn without installing JDK,
Maven, or scip-java locally.

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

# Run the CLI against the bundled fixture
docker compose run --rm shell -lc \
  "stubborn index --scip examples/fixtures/minimal.scip --out /tmp/symbols.db && \
   stubborn context /tmp/symbols.db \
     --target 'semanticdb maven com/example/OrderService#' \
     --format stubborn-dsl"
```

See [docs/STUBBORN-DSL.md](../docs/STUBBORN-DSL.md). Runnable Java demos and
E2E validation live in
[`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo).

## Services

| Service | Purpose |
|---------|---------|
| `shell` | Interactive bash with full toolchain |
| `cli` | Run arbitrary `stubborn` commands |

### Interactive shell

```bash
docker compose run --rm shell
# inside container:
stubborn --help
scip-java --help
```

### One-off CLI

```bash
docker compose run --rm cli --help
```

Mount your own project by editing `docker-compose.yml` or:

```bash
docker compose run --rm \
  -v /path/to/your/java/project:/demo \
  shell
```

## Build arguments

```bash
docker compose build --build-arg SCIP_JAVA_VERSION=0.12.3
```

## Windows notes

- Use Docker Desktop with Linux containers.
- Demo scripts for PowerShell live in `stubborn-demo`.

## Related

- [stubborn-demo](https://github.com/stubborn-ai/stubborn-demo) — demo apps and E2E cases
- [docs/SCIP-INGEST.md](../docs/SCIP-INGEST.md) — SCIP ingest details
