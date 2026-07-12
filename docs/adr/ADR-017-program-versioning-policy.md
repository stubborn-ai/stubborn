# ADR-017: Program versioning policy (multi-repo PyPI line)

- **Status:** Accepted
- **Documented:** 2026-07-12
- **Deciders:** Stubborn maintainers
- **Related:** [ADR-007](ADR-007-java-first-beta-scope.md) (beta scope and 1.0 criteria), [ADR-008](ADR-008-weak-coupling-ecosystem.md) (multi-repo weak coupling), [stubborn-hub RELEASE-CHECKLIST](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/RELEASE-CHECKLIST.md)

## Context

The Stubborn AI program ships four PyPI packages from separate repos:

| PyPI package | Repo |
|--------------|------|
| `stubborn-stub` | `stubborn` |
| `stubborn-mcp` | `stubborn-mcp` |
| `stubborn-watch` | `stubborn-watch` |
| `stubborn-status` | `stubborn-status` |

As of **2026-07**, all four were unified on **`0.10.0b1`**. Prior releases used informal
versioning (alpha `0.9.0a1`, then a coordinated beta bump). Maintainers need a single,
written policy for:

- When to bump major, minor, patch, or beta
- How pre-1.0 minor steps work (`0.9` → `0.10`, not `0.9.1`)
- Canonical vs display version strings (especially `b1`)
- Coordinated vs independent satellite releases
- Git tag format and satellite `stubborn-stub` dependency floors

This ADR is **program-wide** but lives in the `stubborn` repo ADR index because that is
where ecosystem architecture decisions are recorded (ADR-006, ADR-008, ADR-015, ADR-016).
Operational release steps remain in [stubborn-hub RELEASE-CHECKLIST](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/RELEASE-CHECKLIST.md).

### Grandfathering

**`0.10.0b1` is grandfathered.** It was released under the earlier informal beta line.
**ADR-017 applies from the next release onward** (the first version chosen after this ADR
is accepted). Do not retroactively relabel `0.10.0b1` tags or PyPI artifacts.

## Decision

### Version shape

All program packages use **[PEP 440](https://peps.python.org/pep-0440/)** versions:

```text
{major}.{minor}.{patch}[bN]
```

| Segment | When to bump | Example |
|---------|--------------|---------|
| **Major** (`X.0.0`) | Breaking, forward-incompatible API or behavior for published users | `1.0.0` → `2.0.0` |
| **Minor** (`0.X.0`) | New user-facing features, ADRs that change public contracts, or release-worthy capability additions | `0.10.0` → `0.11.0` |
| **Patch** (`0.X.Y`) | Bug fixes, internal refactors, or doc-only corrections that do not warrant a minor | `0.11.0` → `0.11.1` |
| **Beta** (`bN`) | Packaging, CI, metadata, or config-only changes **without** new feature semantics | `0.11.0b1` → `0.11.0b2` |

**Pre-1.0 minor rule:** bump the **minor** integer, not the patch, for feature milestones.
Use `0.9.0` → `0.10.0`, **not** `0.9.1`. After `0.10.0`, the next feature line is
`0.11.0`, then `0.12.0`, and so on.

**Bump discipline (substantial changes):** prefer at least a **minor** step for
release-worthy or user-facing work (new ADRs, packaging semantics, behavior that affects
published users). Avoid patch-only bumps for changes that would normally deserve a minor.
This aligns with maintainer workspace guidance and supersedes informal “patch for anything
small” habits.

### `1.0.0` is a program decision

**`1.0.0` is not automatic** when the minor line reaches `0.99` or similar. The program
explicitly declares **1.0** only after:

- Real-project validation (not demo-only)
- No known major issues in the Java/Spring path ([ADR-007](ADR-007-java-first-beta-scope.md))
- Stable public API and schema contracts the team is willing to support under semver major rules

Until then, stay on `0.X.YbN` with PyPI classifier **Development Status :: 4 - Beta**.

### Beta suffix (`bN`) and display vs canonical

| Role | Rule |
|------|------|
| **Canonical** (required everywhere versions are machine-parsed) | Full PEP 440 string including `bN` when pre-1.0 beta applies |
| **Display** (human-facing docs, hub matrix, changelogs) | May omit **`b1`** when it is the first beta of that `major.minor.patch` line |

**`b1` is the default first beta** of a given `0.X.Y` line. When `b1` is omitted in
display, readers should interpret `0.11.0` as **`0.11.0b1`**.

| Context | Example for first beta of `0.11.0` |
|---------|-------------------------------------|
| `pyproject.toml`, `__version__`, git tags, PyPI, `pip install` | `0.11.0b1` |
| Hub README / release notes (display) | `0.11.0` or `0.11.0b1` (either acceptable) |
| Second packaging-only beta | `0.11.0b2` everywhere (do **not** omit `b2`) |

**PyPI / PEP 440:** always publish the **full** string (e.g. `0.11.0b1`). PyPI has no
concept of “hidden b1”; `pip` and `check_release_matrix.py` compare exact strings. Display
shortening is documentation-only and must not appear in package metadata or tags.

When a **minor** or **patch** bumps, reset beta to **`b1`** on the new line (e.g.
`0.10.0b2` + feature release → `0.11.0b1`, not `0.11.0b3`).

### Unified version line (coordinated releases)

For **coordinated program milestones**, all shipping PyPI packages share **one version
string**:

```text
stubborn-stub     0.11.0b1
stubborn-mcp      0.11.0b1
stubborn-watch    0.11.0b1
stubborn-status   0.11.0b1   (when included in the milestone)
```

Rules:

1. **Hub release matrix** ([`stubborn-hub/README.md`](https://github.com/stubborn-ai/stubborn-hub/blob/main/README.md)) is the canonical documented line for the program.
2. **Coordinated bump:** every package in the milestone gets the same version in
   `pyproject.toml`, module `__version__`, CHANGELOG, and hub matrix.
3. **Rollout order** still applies ([RELEASE-CHECKLIST](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/RELEASE-CHECKLIST.md)): tag `stubborn-stub` first, wait for PyPI, then satellites. Brief skew is allowed during rollout; the hub matrix should reflect the **target** unified version once the milestone is declared.
4. **`stubborn-status`** may ship on an independent cadence for status-only fixes, but
   prefer aligning with the unified line when the change is part of a program release.

### Satellite dependency floors

Satellite packages (`stubborn-mcp`, `stubborn-watch`) declare a **floor** on core:

```text
stubborn-stub>=<core-version-that-was-tested>,<1.0
```

| Rule | Detail |
|------|--------|
| Floor version | The `stubborn-stub` version tagged and tested before the satellite release (usually the current unified line) |
| Upper bound | `<1.0` until the program ships `1.0.0`; then revisit per semver |
| `stubborn-status` | No runtime `stubborn-stub` dependency; invokes sibling CLIs via subprocess ([ADR-016](ADR-016-doctor-status-aggregation.md)) |

Bump the floor in the satellite repo when releasing against a newer core tag. Do not raise
the floor before the core version exists on PyPI.

### Git tags

Format: **`v{canonical-version}`** — include the beta suffix when present.

```text
v0.11.0b1
v0.11.0b2
v1.0.0
```

Tags trigger each package’s `release.yml` workflow (`v*` push). Tag names must match
`pyproject.toml` / `__version__` exactly (including `bN`).

### Choosing a bump (quick reference)

| Change | Bump |
|--------|------|
| New feature, new public tool surface, contract/schema milestone | **Minor** (`0.10.0b1` → `0.11.0b1`) |
| Bug fix, safe refactor, docs typo in shipping repo | **Patch** (`0.11.0b1` → `0.11.1b1`) |
| Workflow, classifier, token, matrix, packaging metadata only | **Beta** (`0.11.0b1` → `0.11.0b2`) |
| Breaking change after 1.0 | **Major** (`1.0.0` → `2.0.0`) |
| Program declares production API | **`1.0.0`** (explicit decision) |

When unsure between patch and minor, **choose minor** for pre-1.0.

## Consequences

### Positive

- One policy for four repos; hub checklist and automation stay aligned
- PEP 440–compatible PyPI and `pip` behavior
- Display shorthand for `b1` reduces matrix noise without lying to package metadata
- Clear path from beta line to deliberate `1.0.0`

### Negative / trade-offs

- Pre-1.0 “minor” integers can grow quickly (`0.10`, `0.11`, …) — intentional, not semver patch semantics
- Coordinated releases require hub matrix + four repos updated in lockstep
- Display/canonical split requires discipline (automation checks canonical strings only)

## Alternatives considered

| Option | Why not |
|--------|---------|
| **ADR in `stubborn-hub` only** | Hub has runbooks, not an ADR index; architecture ADRs already live in `stubborn` |
| **Per-repo semver independently** | Breaks unified beta story and confuses `pip install stubborn-mcp stubborn-stub` |
| **Omit beta suffix entirely on PyPI** | Would publish `0.11.0` as “release” while still beta; misleads classifiers and comparators |
| **Always show `b1` in docs** | Valid but noisier; display omission is opt-in for first beta only |
| **Patch for features (`0.9.1`)** | Contradicts program history (`0.9` → `0.10`) and blurs feature vs fix |

## References

- [ADR-007](ADR-007-java-first-beta-scope.md) — beta scope and 1.0 criteria
- [ADR-008](ADR-008-weak-coupling-ecosystem.md) — multi-repo boundaries
- [stubborn-hub RELEASE-CHECKLIST](https://github.com/stubborn-ai/stubborn-hub/blob/main/docs/RELEASE-CHECKLIST.md) — operational release runbook
- [stubborn-hub `check_release_matrix.py`](https://github.com/stubborn-ai/stubborn-hub/blob/main/scripts/check_release_matrix.py) — version consistency automation
- [PEP 440](https://peps.python.org/pep-0440/) — Python version identification
- [BETA.md](../BETA.md) — current beta scope and KPI baselines
