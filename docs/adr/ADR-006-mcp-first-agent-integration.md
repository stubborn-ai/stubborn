# ADR-006: MCP-first agent integration

- **Status:** Accepted
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

Architecture:

```
stubborn.api  ← single implementation
    ↑
    ├── CLI (Typer)
    ├── MCP server (FastMCP stdio)
    └── tests / scripts
```

MCP tools ([`src/stubborn/mcp_server/server.py`](../../src/stubborn/mcp_server/server.py)):

| Tool | Purpose |
|------|---------|
| `get_context` | Prune + weave for a target |
| `list_symbols` | Search stable IDs by query |
| `metrics` | Stub vs source compression KPI |

Configuration:

- Optional extra: `pip install stubborn-stub[mcp]`
- Default DB via `STUBBORN_DB` or per-call `db_path`
- Project ships [`.cursor/mcp.json`](../../.cursor/mcp.json) for Cursor

Entry points: `stubborn mcp` and `stubborn-mcp` console script.

## Consequences

### Positive

- Agents get typed tools instead of parsing CLI stdout
- Same budgets and weave options as CLI/API — no “MCP-only” behavior drift
- Demo path: `examples/demo-spring/scripts/mcp-smoke.ps1`
- Positions Stubborn as infrastructure for codegen agents, not a standalone REPL tool

### Negative / trade-offs

- MCP SDK is an optional dependency
- stdio transport requires IDE configuration (documented in [MCP.md](../MCP.md))
- Server surface must stay backward compatible once agents depend on tool schemas

## Alternatives considered

| Option | Why not |
|--------|---------|
| **CLI-only** | Agents wrap shell; brittle parsing; higher latency |
| **Custom HTTP API** | Requires running a service; harder for local IDE setup |
| **LSP extension** | Broader scope; SCIP + context compile is not LSP’s job |
| **Duplicate logic in MCP layer** | Would drift from CLI; rejected in favor of `api.py` |

## References

- [MCP.md](../MCP.md)
- [src/stubborn/api.py](../../src/stubborn/api.py)
- [src/stubborn/mcp_server/server.py](../../src/stubborn/mcp_server/server.py)
