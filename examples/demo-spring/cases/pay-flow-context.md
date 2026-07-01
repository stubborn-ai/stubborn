# Case: pay-flow-context

## Goal

Verify **method-level** pruning from `OrderService#payOrder`: includes payment + domain types, emits the target method signature, excludes method bodies.

## Command

```bash
stubborn context metadata/symbols.db \
  --target "<OrderService#payOrder stable_id>" \
  --out metadata/pay-order.stub.java

stubborn metrics metadata/symbols.db \
  --target "<OrderService#payOrder stable_id>" \
  --sources src/main/java
```

Resolve stable id:

```bash
python scripts/resolve_symbol.py metadata/symbols.db payOrder
```

## Expected neighbors

Types and members in the pruned graph should include:

- `payOrder` method signature (target member)
- `PaymentGateway` / `PaymentService` (payment chain)
- `Order`, `OrderRepository`, `OrderResponse`
- `OrderNotFoundException`

## Baseline KPI (demo-spring, local E2E)

| Metric | Value |
|--------|-------|
| `stub_symbols` | ~10 |
| `stub_tokens_est` | ~400 |
| `token_savings` | ≥75% vs full `src/main/java` |

## Notes

- Narrower than [order-service-context](order-service-context.md) (type-level): DTOs like `CreateOrderRequest` may be absent.
- Guard: `scripts/verify_pay_flow_context.py`
- Expected types: `metadata/expected-context-types-pay-order.txt`
