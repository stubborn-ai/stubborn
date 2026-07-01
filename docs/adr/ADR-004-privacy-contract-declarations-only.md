# ADR-004: Privacy contract — declarations only

- **Status:** Accepted
- **Documented:** 2026-07-02
- **Deciders:** Stubborn maintainers

## Context

Enterprises use LLMs on proprietary code. Sending full sources to a model risks leaking:

- Business rules in method bodies
- Literal constants and validation logic
- Annotation attribute values with production data

At the same time, the model **needs** type structure and signatures to generate correct code. Stubborn must draw a clear, enforceable line between **safe context** and **implementation detail**.

## Decision

Stubborn’s **privacy contract** is enforced in weavers, not left to prompt engineering:

### Included in output

- Type declarations (classes, interfaces, enums, records)
- Field and method **signatures** (when weave options allow)
- Optional Javadoc (`--javadoc summary|full`)
- Dependency edges between symbols

### Excluded by design

- Method bodies and implementations
- Field initializers with business values
- Annotation attribute payloads that may carry sensitive data

We emit **stubs** — skeleton declarations comparable to header files — not source dumps. Java stub output may use `{ /* stub */ }` placeholders where a body would exist syntactically, without copying real logic.

This contract applies to **both** output formats (ADR-005) and is a product invariant, not a default users must remember to enable.

## Consequences

### Positive

- Clear story for security review: “context is declaration-level”
- Aligns with token-reduction goals (bodies are most of file size)
- Reduces model temptation to paraphrase hidden logic that was never sent

### Negative / trade-offs

- Models lack local implementation hints for refactors that only touch internals
- Javadoc `full` can still leak semantic detail — teams must treat docs as potentially sensitive
- Privacy ≠ anonymity: type and package names remain visible

## Alternatives considered

| Option | Why not |
|--------|---------|
| **Ship full sources with line ranges** | Defeats token KPI; high leakage risk |
| **Configurable “include bodies” flag** | Invites accidental misuse; hard to audit |
| **Redact only strings matching regex** | Fragile; false sense of security |
| **Encrypt context** | Does not reduce what the model sees once decrypted |

## References

- [POSITIONING.md](../POSITIONING.md) — Privacy contract section
- [src/stubborn/weave/java_stub.py](../../src/stubborn/weave/java_stub.py)
- [src/stubborn/weave/stubborn_dsl.py](../../src/stubborn/weave/stubborn_dsl.py)
