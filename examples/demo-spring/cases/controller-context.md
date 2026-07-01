# Case: controller-context

## Goal

Verify that pruning from `OrderController` includes the web → service chain and request/response DTOs, without method bodies.

## Command

```bash
stubborn context metadata/symbols.db \
  --target "<OrderController stable_id>" \
  --out metadata/order-controller.stub.java

# Optional compact format:
stubborn context metadata/symbols.db \
  --target "<OrderController stable_id>" \
  --format stubborn-dsl \
  --out metadata/order-controller.stubborn-dsl

stubborn metrics metadata/symbols.db \
  --target "<OrderController stable_id>" \
  --sources src/main/java
```

Resolve stable id:

```bash
python scripts/resolve_symbol.py metadata/symbols.db OrderController
```

## Expected neighbors

Types in the pruned graph should include:

- `OrderController` (target)
- `OrderService` (injected service)
- `CreateOrderRequest`, `OrderResponse` (API DTOs)
- `Order` (domain type via service/repository chain)

## Baseline KPI (demo-spring, local E2E)

| Metric | Value |
|--------|-------|
| `stub_symbols` | ~9 |
| `stub_tokens_est` | ~375 |
| `token_savings` | ≥75% vs full `src/main/java` |

## Notes

- Controller target emphasizes **HTTP layer → service**; repository types may appear at depth 2 via `OrderService`.
- Guard script: `scripts/verify_controller_context.py`
- Expected type list: `metadata/expected-context-types-controller.txt`
