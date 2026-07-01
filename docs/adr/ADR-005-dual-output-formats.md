# ADR-005: Dual output formats — `java-stub` and `stubborn-dsl`

- **Status:** Accepted
- **Documented:** 2026-07-02
- **Deciders:** Stubborn maintainers

## Context

One pruned graph must serve different LLM tasks:

- **Java / Spring codegen** — models perform best on familiar Java-like syntax
- **Architecture / audit / migration mapping** — token budget dominates; graph structure matters more than syntax sugar

A single output format forces a trade-off on every call. We also need a **versioned** compact format so agents can parse graphs reliably without guessing.

## Decision

After pruning, **weave** to one of two formats via [`src/stubborn/weave/dispatch.py`](../../src/stubborn/weave/dispatch.py):

| Format | Since | Purpose |
|--------|-------|---------|
| `java-stub` | v0.1 | Java-like declarations; default for codegen |
| `stubborn-dsl` | v0.7 | Compact type/edge graph; lower token cost |

Shared rules:

- Same `PrunedGraph` input for both
- Same weave granularity switches: `--member-signatures`, `--javadoc` ([STUBBORN-DSL-GUIDE.md](../STUBBORN-DSL-GUIDE.md))
- `stubborn-dsl` grammar version in header line: `stubborn-dsl/1.0` (breaking changes bump minor version)

Each `stubborn-dsl` block embeds a short `# Guide` header (~30 tokens) so models see the legend inline; [STUBBORN-DSL-LLM.txt](../STUBBORN-DSL-LLM.txt) is optional for system prompts.

**User choice:** callers pick `--format` per invocation. Pure Java projects default to `java-stub`; mixed-language or token-sensitive tasks opt into `stubborn-dsl`. Long-term polyglot value is the primary strategic reason to keep DSL alongside language-specific weavers (see [STUBBORN-DSL-GUIDE.md](../STUBBORN-DSL-GUIDE.md)).

## Consequences

### Positive

- Callers pick format per task without re-indexing
- MCP / API expose `format` as a first-class parameter
- Compression KPIs can compare formats on the same index (demo-spring ~10–30% token delta on small graphs; larger on petclinic)

### Negative / trade-offs

- Two weavers to maintain (`java_stub.py`, `stubborn_dsl.py`)
- Agents must choose format — mitigated by decision guide docs
- `stubborn-dsl` has learning curve; java-stub remains default

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Java-stub only** | Token cost on large graphs; weak for graph-first tasks |
| **JSON/graph-only API output** | Verbose; poor LLM ergonomics without custom prompting |
| **Markdown prose summaries** | Non-deterministic if model-generated; not reproducible in CI |
| **Single auto-selected format** | Hides trade-off; surprises users on token bills |

## References

- [STUBBORN-DSL.md](../STUBBORN-DSL.md) — grammar spec
- [STUBBORN-DSL-GUIDE.md](../STUBBORN-DSL-GUIDE.md) — when to use which
- [src/stubborn/weave/dispatch.py](../../src/stubborn/weave/dispatch.py)
