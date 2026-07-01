# Beta readiness (Java-first)

**Current: Beta `0.9.0b3`** — Java/Spring E2E validated; `Development Status :: 4 - Beta`.

Pre-beta (`0.9.0a1`) completed the checklist; this tag flips the PyPI classifier and version line.

## Who this beta serves

| Audience | Beta fit |
|----------|----------|
| **Primary** — Java/Spring teams with SCIP in CI or runbooks | **Strong** — E2E, KPIs, `diff`, verify guards |
| **Secondary** — Cursor/MCP individuals | **Good** if you accept SCIP/index setup; start with fixture or Docker |
| **Any language via SCIP** | **Experimental ingest only** — no weave/E2E claim |

See [POSITIONING.md](POSITIONING.md) for the full primary/secondary split.

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
- [x] Type-neighbor pruning + token budget + `--prune-mode`
- [x] `java-stub` + `stubborn-dsl` weavers (user choice)
- [x] Target-type method signatures (v0.9); neighbor/all + Javadoc via weave switches

### E2E validation

- [x] demo-spring Docker E2E (OrderService, OrderController, payOrder)
- [x] spring-petclinic scale-up E2E
- [x] Duke's Bank `AccountControllerBean` case (Step 7 runbook)
- [x] CI symbols.db artifact — neighbor tests without skip

### Agent / docs

- [x] STUBBORN-DSL grammar, LLM snippet, format guide
- [x] PyPI `stubborn-stub` published (`0.9.0b3`)
- [x] ADRs + honest positioning ([POSITIONING.md](POSITIONING.md))

### Quality bar

- [x] `language: java` from SCIP
- [x] pytest 3.11–3.13 + ruff CI
- [x] PR symbol-diff workflow
- [x] `pyproject.toml` classifier → **Beta**

## Out of scope for 1.0

| Item | Target |
|------|--------|
| Zero-config repo indexing (no SCIP) | Out of scope — use IDE/repo-map tools |
| scip-clang / TypeScript **weave E2E** | v1.0+ |
| Polyglot merged index story | v1.0+ ADR + E2E |
| Method signatures on non-target types by default | v1.0+ — use `--member-signatures neighbors|all` (beta) |
| Rich Javadoc in output | v1.0+ — use `--javadoc full` (beta) |
| Petclinic on every PR | Weekly (cost) |

## Known limitations (beta)

1. **Java-first** — production claims apply to scip-java path only; other languages ingest at your own risk.
2. **SCIP prerequisite** — every real project needs an indexer before Stubborn; not plug-and-play vs repo-map tools.
3. **Neighbor honesty** — default `--prune-mode smart` uses signature heuristics; use **`strict`** for SCIP-only edges ([ADR-003](adr/ADR-003-type-neighbor-pruning.md)).
4. **Method signatures** — default `target` only; use `--member-signatures neighbors|all` for more.
5. **Token estimate** — chars/4 heuristic.
6. **Javadoc** — default summary (java-stub) / off (stubborn-dsl); `--javadoc full` for `@param` tags.
7. **Stubborn-DSL** — user choice for token/graph tasks; `java-stub` default for Java codegen ([STUBBORN-DSL-GUIDE.md](STUBBORN-DSL-GUIDE.md)).
8. **Dual audience** — reconcile/CI features target enterprise migration workflows; MCP targets agents — see [POSITIONING.md](POSITIONING.md).

## KPI baselines

Java E2E only (`--prune-mode smart`):

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
- [adr/README.md](adr/README.md)
