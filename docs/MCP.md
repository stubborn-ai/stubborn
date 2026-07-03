# MCP server

The MCP server lives in the **[stubborn-mcp](https://github.com/stubborn-ai/stubborn-mcp)** package ([PyPI](https://pypi.org/project/stubborn-mcp/)).

## Install

```bash
pip install stubborn-stub stubborn-mcp
```

Build an index with the core compiler:

```bash
stubborn index --scip index.scip --out metadata/symbols.db
export STUBBORN_DB=metadata/symbols.db
stubborn-mcp
```

## Documentation

- [stubborn-mcp README](https://github.com/stubborn-ai/stubborn-mcp/blob/main/README.md)
- [stubborn-mcp docs/MCP.md](https://github.com/stubborn-ai/stubborn-mcp/blob/main/docs/MCP.md) — tools, parameters, Cursor config

## Architecture

MCP tools delegate to [`stubborn.api`](src/stubborn/api.py). See [ADR-006](adr/ADR-006-mcp-first-agent-integration.md).
