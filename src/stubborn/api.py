"""Structured API for CLI, MCP, and other integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.metrics import compute_compression
from stubborn.store.reader import SymbolRecord, list_symbols, resolve_db_path
from stubborn.store.writer import IndexInfo, read_info
from stubborn.weave.dispatch import weave_context
from stubborn.weave.options import WeaveOptions


@dataclass(frozen=True)
class ContextResult:
    target_stable_id: str
    format: str
    text: str
    symbol_count: int
    estimated_tokens: int
    dropped_for_budget: bool


def _budget(
    *,
    max_symbols: int,
    call_depth: int,
    max_tokens: int,
) -> ContextBudget:
    return ContextBudget(
        call_closure_depth=call_depth,
        max_symbols=max_symbols,
        max_tokens=max_tokens,
    )


def get_context(
    target: str,
    *,
    db_path: str | Path | None = None,
    format: str = "java-stub",
    max_symbols: int = 200,
    call_depth: int = 2,
    max_tokens: int = 12_000,
    member_signatures: str = "target",
    javadoc: str | None = None,
) -> ContextResult:
    """Prune symbol graph and weave LLM context for a target symbol."""
    path = resolve_db_path(db_path)
    budget = _budget(
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
    )
    weave_options = WeaveOptions(member_signatures=member_signatures, javadoc=javadoc)
    graph = prune_context(path, target, budget=budget)
    result = weave_context(
        graph,
        format=format,
        max_tokens=budget.max_tokens,
        options=weave_options,
    )
    return ContextResult(
        target_stable_id=target,
        format=format,
        text=result.text,
        symbol_count=result.symbol_count,
        estimated_tokens=result.estimated_tokens,
        dropped_for_budget=result.dropped_for_budget,
    )


def list_index_symbols(
    *,
    db_path: str | Path | None = None,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    index_run_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return symbol records as JSON-serializable dicts."""
    path = resolve_db_path(db_path)
    records = list_symbols(
        path,
        query=query,
        kind=kind,
        limit=limit,
        index_run_id=index_run_id,
    )
    return [asdict(record) for record in records]


def get_index_info(
    *,
    db_path: str | Path | None = None,
    index_run_id: int | None = None,
) -> dict[str, Any]:
    """Return index run summary as a JSON-serializable dict."""
    path = resolve_db_path(db_path)
    info: IndexInfo = read_info(path, index_run_id=index_run_id)
    return {
        "index_run_id": info.index_run_id,
        "scip_source": info.scip_source,
        "language": info.language,
        "indexed_at": info.indexed_at,
        "symbol_count": info.symbol_count,
        "edge_count": info.edge_count,
        "db_path": str(path),
    }


def get_metrics(
    target: str,
    sources: str | Path,
    *,
    db_path: str | Path | None = None,
    max_symbols: int = 200,
    call_depth: int = 2,
    max_tokens: int = 12_000,
    format: str = "java-stub",
    member_signatures: str = "target",
    javadoc: str | None = None,
) -> dict[str, Any]:
    """Return compression KPI as a JSON-serializable dict."""
    path = resolve_db_path(db_path)
    budget = _budget(
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
    )
    weave_options = WeaveOptions(member_signatures=member_signatures, javadoc=javadoc)
    report = compute_compression(
        path,
        target,
        sources,
        budget=budget,
        format=format,
        options=weave_options,
    )
    return {
        "target_stable_id": report.target_stable_id,
        "db_path": str(path),
        "sources": str(Path(sources)),
        "source_files": report.source.file_count,
        "source_bytes": report.source.byte_count,
        "source_tokens_est": report.source.estimated_tokens,
        "stub_symbols": report.stub.symbol_count,
        "stub_bytes": len(report.stub.text.encode("utf-8")),
        "stub_tokens_est": report.stub.estimated_tokens,
        "compression_ratio": round(report.compression_ratio, 4),
        "token_savings_percent": round(report.token_savings_percent, 1),
        "dropped_for_budget": report.stub.dropped_for_budget,
        "stub_text": report.stub.text,
    }
