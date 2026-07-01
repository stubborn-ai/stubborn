# When to use `java-stub` vs `stubborn-dsl`

**User choice** — both formats share the same prune step; pick per task:

| Situation | Format |
|-----------|--------|
| Pure Java / Spring — editing or generating source | `java-stub` |
| Mixed-language repo, migration mapping, architecture audit | `stubborn-dsl` |
| Tight token budget on a large graph | `stubborn-dsl` + consider `--prune-mode fast` |

Quick decision guide for agents and prompt authors.

## Decision tree

```
Generating or editing Java/Spring source code?
├─ YES → java-stub (default)
└─ NO  → Is token budget tight or task graph-first (deps, design, migration mapping)?
         ├─ YES → stubborn-dsl (+ STUBBORN-DSL-LLM.txt in system prompt)
         └─ NO  → java-stub
```

## Format comparison

| | `java-stub` | `stubborn-dsl` |
|---|-------------|--------------|
| **Looks like** | Java declarations | Compact type/edge graph |
| **LLM familiarity** | High (Java syntax) | Medium (3-line `# Guide` in each block) |
| **Token cost** | Higher | Lower on large graphs (~10–30% on demo-spring; fixed Guide overhead on tiny graphs) |
| **Best tasks** | Codegen, refactor in place | Architecture, dependency audit, migration scoping |
| **Method target** | Emits target method line | `member m Type.method sig` |
| **Type target (v0.9+)** | Target class includes method signatures | `members:` block on target type |

## Granularity switches (token vs detail)

Both formats share `--member-signatures` and `--javadoc` (CLI, API, MCP):

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--member-signatures` | `off` \| `target` \| `neighbors` \| `all` | `target` | Which types get method lists |
| `--javadoc` | `off` \| `summary` \| `full` | `summary` (java-stub), `off` (stubborn-dsl) | Doc comments in output |

| Task | Suggested flags |
|------|-----------------|
| Codegen on target class | `target` + `summary` |
| Min tokens | `off` + `off` + `stubborn-dsl` |
| Understand neighbor APIs | `neighbors` or `all` |
| Business semantics | `summary` or `full` on key types |

## Examples (demo-spring, same index)

| Target | Format | ~tokens | Use when |
|--------|--------|---------|----------|
| `OrderService#` | java-stub | ~463 | Implement service methods |
| `OrderService#` | stubborn-dsl | ~350 | See service deps cheaply |
| `OrderController#` | java-stub | ~375 | Add REST endpoints |
| `OrderService#payOrder` | either | ~400 | Narrow payment-flow change |

Run locally:

```bash
stubborn context metadata/symbols.db --target "<stable_id>" --format java-stub
stubborn context metadata/symbols.db --target "<stable_id>" --format stubborn-dsl
stubborn metrics metadata/symbols.db --target "<stable_id>" --sources src/main/java
```

## MCP

```json
{ "target": "…OrderService#", "format": "java-stub" }
{ "target": "…OrderService#", "format": "stubborn-dsl" }
```

## Rules of thumb

1. **Default to `java-stub`** for Cursor/Copilot Java tasks.
2. **Use `stubborn-dsl`** when context is read-only (analysis, mapping, review) or you hit `max_tokens`.
3. **Method targets** (`Type#method`) work in both formats; prefer `java-stub` if the model must edit that method.
4. Paste [STUBBORN-DSL-LLM.txt](STUBBORN-DSL-LLM.txt) once per session when using `stubborn-dsl`.

## Related

- [STUBBORN-DSL.md](STUBBORN-DSL.md) — grammar
- [STUBBORN-DSL-LLM.txt](STUBBORN-DSL-LLM.txt) — system prompt snippet
- [BETA.md](BETA.md) — release status
