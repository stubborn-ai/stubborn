# orders-demo — Stubborn E2E

A **small, modern** Spring Boot 3 application used as the primary end-to-end example for Stubborn.

| | |
|---|---|
| Java | 21 |
| Framework | Spring Boot 3.3 |
| Build | Maven |
| Domain | Orders API (controller → service → repository) |
| Source files | ~14 Java classes |

Designed to be extended with additional **cases** under [`cases/`](cases/) without growing into a monolith.

## Layout

```text
com.example.orders
├── OrdersApplication
├── web/          OrderController, OrderExceptionHandler
├── service/      OrderService, PaymentService, PaymentGateway
├── repository/   OrderRepository, InMemoryOrderRepository
├── domain/       Order, Customer, OrderStatus
├── dto/          CreateOrderRequest, OrderResponse
└── exception/    OrderNotFoundException
```

## Prerequisites

Choose **one** path:

### A. Docker (recommended — no local JDK/Maven/scip-java)

From the **stubborn repo root**:

```bash
docker compose build
docker compose run --rm e2e
```

See [docker/README.md](../../docker/README.md).

### B. Host toolchain

- **JDK 21+**
- **Maven 3.9+**
- **[scip-java](https://github.com/sourcegraph/scip-java)** on `PATH`
- **Stubborn** installed: `pip install -e ".[dev]"` from repo root

## Quick E2E (PowerShell, host)

```powershell
cd examples/demo-spring
./scripts/run-e2e.ps1
```

Outputs:

- `index.scip` — SCIP index from scip-java
- `metadata/symbols.db` — Stubborn SQLite graph
- `metadata/order-service.stub.java` — pruned LLM context for `OrderService` (`java-stub`)

Optional compact format:

```bash
stubborn context metadata/symbols.db \
  --target "<OrderService stable_id>" \
  --format stubborn-dsl \
  --out metadata/order-service.stubborn-dsl
```

See [docs/STUBBORN-DSL.md](../../docs/STUBBORN-DSL.md).

## Manual steps

```bash
# 1. Compile (scip-java index also compiles via Maven)
mvn -q -DskipTests package

# 2. Generate SCIP index
scip-java index
# → index.scip

# 3. Ingest into Stubborn
stubborn index --scip index.scip --out metadata/symbols.db
stubborn info metadata/symbols.db

# 4. Resolve target symbol (display name → stable_id)
#    Then emit context — exact stable_id depends on scip-java output, e.g.:
stubborn context metadata/symbols.db \
  --target "<OrderService stable_id from index>" \
  --out metadata/order-service.stub.java
```

Use the E2E script to resolve `OrderService` automatically from the SQLite index.

## Cursor MCP (v0.4)

With the **stubborn repo root** open as the Cursor workspace:

1. Install: `pip install -e ".[mcp]"` from repo root
2. Ensure `metadata/symbols.db` exists (`./scripts/run-e2e.ps1` or index step above)
3. Project config is already at [`.cursor/mcp.json`](../../.cursor/mcp.json) — enables server `stubborn`
4. **Cursor Settings → MCP** → enable `stubborn` (green) → Reload if needed

Smoke-test without Cursor:

```powershell
./scripts/mcp-smoke.ps1
```

Agent workflow:

1. `list_symbols` with `query: "OrderService"`
2. `get_context` with the returned `stable_id`
3. `metrics` with `sources: examples/demo-spring/src/main/java`

See [docs/MCP.md](../../docs/MCP.md).

## Run the app (optional)

```bash
mvn spring-boot:run
curl -X POST http://localhost:8080/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"customerEmail":"ada@example.com","customerName":"Ada","total":42.50}'
```

## Adding cases

See [`cases/README.md`](cases/README.md) for the case catalog pattern. New scenarios (e.g. pay flow, exception paths) should add focused docs and optional expected stub snippets — not more framework boilerplate.

## Related examples

| Example | Role |
|---------|------|
| [spring-petclinic](../spring-petclinic/) | Scale-up E2E vs official PetClinic (~375 symbols, ~90% savings) |
| [migration-bridge](../migration-bridge/) | Legacy migration integration (Duke's Bank) |
| [fixtures](../fixtures/) | Minimal SCIP files for unit tests |
