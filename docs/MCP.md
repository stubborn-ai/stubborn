# MCP server

Stubborn exposes three MCP tools over **stdio** for Cursor, Claude Desktop, and other MCP clients.

## Install

```bash
pip install stubborn-stub[mcp]
```

From a git checkout:

```bash
pip install -e ".[mcp]"
# or for development
pip install -e ".[dev]"
```

## Tools

| Tool | Purpose |
|------|---------|
| `get_context` | Prune symbol graph → LLM context (`format`: `java-stub` or `stubborn-dsl`; `prune_mode`: `smart`, `strict`, `fast`) |
| `list_symbols` | Browse/search indexed symbols to pick a target |
| `metrics` | Compression KPI: stub vs full Java `sources` tree |

### Database path

Pass `db_path` on each call, or set a default:

```bash
export STUBBORN_DB=/path/to/metadata/symbols.db
```

## Run

```bash
stubborn mcp
# or
stubborn-mcp
```

The server uses stdio transport (default for local IDE integration).

## Cursor configuration

Add to `.cursor/mcp.json` (project) or Cursor MCP settings:

```json
{
  "mcpServers": {
    "stubborn": {
      "command": "stubborn-mcp",
      "env": {
        "STUBBORN_DB": "${workspaceFolder}/examples/demo-spring/metadata/symbols.db"
      }
    }
  }
}
```

If the CLI is not on `PATH`, use the module entry:

```json
{
  "mcpServers": {
    "stubborn": {
      "command": "python",
      "args": ["-m", "stubborn.mcp_server.server"],
      "env": {
        "STUBBORN_DB": "${workspaceFolder}/metadata/symbols.db"
      }
    }
  }
}
```

### Typical agent workflow

1. `stubborn index --scip index.scip --out metadata/symbols.db`
2. Configure MCP with `STUBBORN_DB` pointing at that file
3. Agent calls `list_symbols` with `query: "OrderService"` to find `stable_id`
4. Agent calls `get_context` with the target stable_id before generating code
   - `format: "java-stub"` — default; Java-like declarations
   - `format: "stubborn-dsl"` — compact graph; see [STUBBORN-DSL-LLM.txt](STUBBORN-DSL-LLM.txt)
   - `member_signatures` / `javadoc` — tune detail vs tokens ([guide](STUBBORN-DSL-GUIDE.md#granularity-switches-token-vs-detail))
5. Optional: `metrics` with `sources: src/main/java` for compression reporting

## Parameters (get_context)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `target` | required | SCIP stable_id |
| `db_path` | `STUBBORN_DB` | Symbol graph SQLite file |
| `max_tokens` | 12000 | Output token budget (chars/4) |
| `max_symbols` | 200 | Graph prune cap |
| `call_depth` | 2 | Reference closure depth |
| `format` | `java-stub` | `java-stub` or `stubborn-dsl` ([grammar](STUBBORN-DSL.md), [LLM prompt snippet](STUBBORN-DSL-LLM.txt)) |
| `member_signatures` | `target` | `off` \| `target` \| `neighbors` \| `all` — method lists on types |
| `javadoc` | format default | `off` \| `summary` \| `full` — doc comments (`summary` for java-stub, `off` for stubborn-dsl) |

`metrics` accepts the same `member_signatures` and `javadoc` parameters.

## Related

- [STUBBORN-DSL.md](STUBBORN-DSL.md) — compact output format
- [INTEGRATION.md](INTEGRATION.md) — optional anchor-migration program integration
