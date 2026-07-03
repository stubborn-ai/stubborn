# ADR-006: MCP-first agent integration

- **Status:** Accepted (amended 2026-07-03 — MCP moved to `stubborn-mcp` repo)
- **Documented:** 2026-07-02
- **Deciders:** Stubborn maintainers

## Context

Primary users include **IDE agents** (Cursor, Copilot-style workflows) that need to:

1. Discover symbols by name (`OrderService`)
2. Pull pruned context for a `stable_id`
3. Report compression metrics for budgeting

CLI alone forces shell orchestration in every agent loop. A structured protocol reduces friction and documents the intended agent surface.

## Decision

Expose agent functionality through **Model Context Protocol (MCP)** as a first-class integration, alongside CLI and Python API.

**Implementation split (2026-07-03):** the MCP transport ships in **[stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)**. This repo (`stubborn`) owns `stubborn.api` only.

Architecture:

```
stubborn.api  ← single implementation (stubborn repo)
    ↑
    ├── CLI (Typer)
    ├── stubborn-mcp (FastMCP stdio)  ← separate package/repo
    └── tests / scripts
```

MCP tools ([`stubborn-mcp`](https://github.com/stubborn-ai/stubborn-mcp/blob/main/src/stubborn_mcp/server.py)):

| Tool | Purpose |
|------|---------|
| `get_context` | Prune + weave for a target |
| `list_symbols` | Search stable IDs by query |
| `metrics` | Stub vs source compression KPI |

Configuration:

- Install: `pip install stubborn-mcp` (depends on `stubborn-stub`)
- Default DB via `STUBBORN_DB` or per-call `db_path`
- Example [`.cursor/mcp.json`](../../.cursor/mcp.json) uses `command: stubborn-mcp`

Entry point: `stubborn-mcp` console script (or `python -m stubborn_mcp`).

## Consequences

### Positive

- Agents get typed tools instead of parsing CLI stdout
- Same budgets and weave options as CLI/API — no “MCP-only” behavior drift
- Core package stays free of MCP SDK dependency
- Demo path: [`stubborn-demo/demo-spring/scripts/mcp-smoke.ps1`](https://github.com/stubborn-ai/stubborn-demo/blob/main/demo-spring/scripts/mcp-smoke.ps1)
- Positions Stubborn as infrastructure for codegen agents, not a standalone REPL tool

### Negative / trade-offs

- Two packages to install for MCP users (`stubborn-stub` + `stubborn-mcp`)
- stdio transport requires IDE configuration (documented in [stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp/blob/main/docs/MCP.md))
- MCP tool schemas must stay backward compatible once agents depend on them

## Alternatives considered

| Option | Why not |
|--------|---------|
| **CLI-only** | Agents wrap shell; brittle parsing; higher latency |
| **Custom HTTP API** | Requires running a service; harder for local IDE setup |
| **LSP extension** | Broader scope; SCIP + context compile is not LSP’s job |
| **Duplicate logic in MCP layer** | Would drift from CLI; rejected in favor of `api.py` |
| **MCP bundled in `stubborn-stub` forever** | Optional extra complicated core PyPI package; split for independent agent release cadence |

## References

- [MCP.md](../MCP.md) — pointer to stubborn-mcp
- [src/stubborn/api.py](../../src/stubborn/api.py)
- [stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)
