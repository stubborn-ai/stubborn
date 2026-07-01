"""stdio MCP server exposing Stubborn tools to agents."""

from __future__ import annotations

from typing import Any

from stubborn.api import (
    get_context as build_context,
)
from stubborn.api import (
    get_index_info,
    list_index_symbols,
)
from stubborn.api import (
    get_metrics as build_metrics,
)
from stubborn.weave.stubborn_dsl_llm import llm_guide_text

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised via optional extra
    raise ImportError(
        "MCP support requires the mcp package. Install with: pip install 'stubborn-stub[mcp]'"
    ) from exc

mcp = FastMCP(
    "stubborn",
    instructions=(
        "Deterministic code context from SCIP symbol graphs. "
        "Use get_context for pruned stub text (java-stub or stubborn-dsl), list_symbols to find stable_id targets, "
        "and metrics for compression KPIs. Set STUBBORN_DB or pass db_path per call. "
        f"When format is stubborn-dsl: {llm_guide_text()}"
    ),
)


@mcp.tool()
def get_context(
    target: str,
    db_path: str | None = None,
    format: str = "java-stub",
    max_symbols: int = 200,
    call_depth: int = 2,
    max_tokens: int = 12_000,
    member_signatures: str = "target",
    javadoc: str | None = None,
    prune_mode: str = "smart",
) -> dict[str, Any]:
    """Return pruned, privacy-safe stub context for an LLM target symbol.

    format=stubborn-dsl: compact graph text; each block includes a 3-line # Guide header.
    See docs/STUBBORN-DSL-LLM.txt for a system-prompt snippet.

    member_signatures: off | target | neighbors | all — controls method lists on types.
    javadoc: off | summary | full — default summary (java-stub) or off (stubborn-dsl).
    prune_mode: smart (SCIP + signature heuristics) | strict (SCIP edges only) | fast (smaller neighborhood).
    """
    result = build_context(
        target,
        db_path=db_path,
        format=format,
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
        member_signatures=member_signatures,
        javadoc=javadoc,
        prune_mode=prune_mode,
    )
    return {
        "target_stable_id": result.target_stable_id,
        "format": result.format,
        "text": result.text,
        "symbol_count": result.symbol_count,
        "estimated_tokens": result.estimated_tokens,
        "dropped_for_budget": result.dropped_for_budget,
    }


@mcp.tool()
def list_symbols(
    db_path: str | None = None,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List indexed symbols to help pick a context target stable_id."""
    symbols = list_index_symbols(
        db_path=db_path,
        query=query,
        kind=kind,
        limit=limit,
    )
    info = get_index_info(db_path=db_path)
    return {
        "db_path": info["db_path"],
        "index_run_id": info["index_run_id"],
        "symbol_count": info["symbol_count"],
        "returned": len(symbols),
        "symbols": symbols,
    }


@mcp.tool()
def metrics(
    target: str,
    sources: str,
    db_path: str | None = None,
    max_symbols: int = 200,
    call_depth: int = 2,
    max_tokens: int = 12_000,
    member_signatures: str = "target",
    javadoc: str | None = None,
    prune_mode: str = "smart",
    include_stub_text: bool = False,
) -> dict[str, Any]:
    """Compare pruned stub size against full Java sources (compression KPI)."""
    report = build_metrics(
        target,
        sources,
        db_path=db_path,
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
        member_signatures=member_signatures,
        javadoc=javadoc,
        prune_mode=prune_mode,
    )
    if not include_stub_text:
        report = {k: v for k, v in report.items() if k != "stub_text"}
    return report


def main() -> None:
    """Run the MCP server over stdio (default transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
