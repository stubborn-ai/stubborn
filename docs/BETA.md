# Beta readiness (Java-first)

**Current: Beta `0.9.0b3`** — Java/Spring E2E validated; `Development Status :: 4 - Beta`.

Pre-beta (`0.9.0a1`) completed the checklist; this tag flips the PyPI classifier and version line.

## Versioning

| Stage | Version | Classifier |
|-------|---------|------------|
| Pre-beta | `0.9.0a1` | Alpha |
| **Beta (now)** | **`0.9.0b3`** | **Beta** |
| Stable | `1.0.0` | Stable |

## Beta checklist (complete)

### Core pipeline

- [x] SCIP binary + NDJSON + JSON fixture ingest
- [x] SQLite symbol graph + CLI + MCP
- [x] Type-neighbor pruning + token budget
- [x] `java-stub` + `stubborn-dsl` weavers
- [x] Target-type method signatures (v0.9); neighbor/all + Javadoc via weave switches

### E2E validation

- [x] demo-spring Docker E2E (OrderService, OrderController, payOrder)
- [x] spring-petclinic scale-up E2E
- [x] Duke's Bank `AccountControllerBean` case (Step 7 runbook)
- [x] CI symbols.db artifact — neighbor tests without skip

### Agent / docs

- [x] STUBBORN-DSL grammar, LLM snippet, format guide
- [x] PyPI `stubborn-stub` published (`0.9.0b2`)

### Quality bar

- [x] `language: java` from SCIP
- [x] pytest 3.11–3.13
- [x] PR symbol-diff workflow
- [x] `pyproject.toml` classifier → **Beta** (`0.9.0b2`)

## Out of scope for 1.0

| Item | Target |
|------|--------|
| PyPI publish | **Done** — `pip install stubborn-stub` |
| scip-clang / TypeScript E2E | v1.0+ |
| Method signatures on non-target types | v1.0+ — use `--member-signatures neighbors|all` (beta) |
| Rich Javadoc in output | v1.0+ — use `--javadoc full` (beta) |
| Petclinic on every PR | Weekly (cost) |

## Known limitations (beta)

1. **Java-first** — validated with scip-java.
2. **Method signatures** — default `target` only; use `--member-signatures neighbors|all` for more.
3. **Token estimate** — chars/4 heuristic.
4. **Javadoc** — default summary (java-stub) / off (stubborn-dsl); `--javadoc full` for `@param` tags.
5. **Stubborn-DSL** — see [STUBBORN-DSL-GUIDE.md](STUBBORN-DSL-GUIDE.md).
6. **SCIP is the index** — Stubborn compiles pruned graphs to LLM text.

## KPI baselines

| Example | Target | Token savings |
|---------|--------|---------------|
| demo-spring `OrderService` | service | ~81% |
| demo-spring `OrderController` | web | ~84% |
| demo-spring `OrderService#payOrder` | method | ~80% |
| spring-petclinic `VetController` | scale-up | ~90% |
| dukesbank `AccountControllerBean` | migration | ≥70% (Step 7) |

## Related

- [POSITIONING.md](POSITIONING.md)
- [INTEGRATION.md](INTEGRATION.md)
