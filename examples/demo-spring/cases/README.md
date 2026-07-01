# E2E cases — demo-spring

Catalog of focused scenarios for validating Stubborn on this demo app.
Add a new case by creating a markdown file here and (optionally) a script snippet in `../scripts/`.

| Case | Status | Target symbol | What we learn |
|------|--------|---------------|---------------|
| [order-service-context](order-service-context.md) | Active | `OrderService` | Service-layer pruning: repo + payment + DTOs |
| [controller-context](controller-context.md) | Active | `OrderController` | Web layer → service dependencies |
| [pay-flow-context](pay-flow-context.md) | Active | `OrderService#payOrder` | Method-level narrow context |

## Case template

```markdown
# case-name

## Goal
One sentence.

## Command
stubborn context ... --target "..."

## Expected neighbors
- ClassA
- ClassB

## Notes
Token count, edge cases, etc.
```
