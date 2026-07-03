# Examples

Core fixtures and legacy in-repo examples for Stubborn.

The canonical runnable demo and validation projects are moving to
[`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo), so the core repo
can stay focused on headless ingest, store, prune, weave, API, and CLI behavior.
Minimal fixtures remain here for unit and contract tests.

| Example | Status | Description |
|---------|--------|-------------|
| [demo-spring](demo-spring/) | Legacy / mirrored | Spring Boot 3 demo; canonical copy moves to `stubborn-demo` |
| [fixtures](fixtures/) | Active | Minimal JSON / binary SCIP for unit tests |
| [spring-petclinic](spring-petclinic/) | Legacy / mirrored | Scale-up E2E vs official PetClinic (~375 symbols, ~90% savings) |
| [dukesbank](dukesbank/) | Legacy / mirrored | Duke's Bank Step 7 — external clone + E2E |
| [migration-bridge](migration-bridge/) | Legacy / mirrored | Optional anchor-migration consumer sketch |

## Output formats

Both examples support:

- `java-stub` (default) — Java-like declarations for codegen
- `stubborn-dsl` — compact type/edge graph ([docs/STUBBORN-DSL.md](../docs/STUBBORN-DSL.md))

## Recommended first run

Use [`stubborn-demo`](https://github.com/stubborn-ai/stubborn-demo) for product
demos and validation:

```bash
git clone https://github.com/stubborn-ai/stubborn-demo
cd stubborn-demo/demo-spring
./scripts/run-e2e.ps1   # Windows PowerShell
```

## Documentation

- [docs/README.md](../docs/README.md) — full doc index
- [docker/README.md](../docker/README.md) — toolchain image
