"""Structured API for CLI, MCP, and other integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from stubborn.config import ContextBudget, apply_prune_mode
from stubborn.graph.prune import prune_context
from stubborn.ingest.contracts import contract_snapshot_from_manifest
from stubborn.ingest.openapi import openapi_snapshot_from_file
from stubborn.metrics import compute_compression
from stubborn.store.reader import (
    list_contract_endpoints,
    list_symbols,
    resolve_db_path,
    workspace_run_summaries,
)
from stubborn.store.writer import IndexInfo, IndexWriter, read_info
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
    contract_edges: list[dict[str, Any]] = field(default_factory=list)
    contract_endpoints: list[dict[str, Any]] = field(default_factory=list)
    contract_evidence_summary: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractIndexResult:
    index_run_id: int
    db_path: str
    manifest_path: str
    workspace: str | None
    repo_key: str | None
    endpoint_count: int
    binding_count: int
    run_kind: str = "contract"


def _budget(
    *,
    max_symbols: int,
    call_depth: int,
    max_tokens: int,
    prune_mode: str = "smart",
) -> ContextBudget:
    return apply_prune_mode(
        ContextBudget(
            call_closure_depth=call_depth,
            max_symbols=max_symbols,
            max_tokens=max_tokens,
            prune_mode=prune_mode,
        )
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
    prune_mode: str = "smart",
    workspace: str | None = None,
    repo_key: str | None = None,
) -> ContextResult:
    """Prune symbol graph and weave LLM context for a target symbol."""
    path = resolve_db_path(db_path)
    budget = _budget(
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
        prune_mode=prune_mode,
    )
    weave_options = WeaveOptions(member_signatures=member_signatures, javadoc=javadoc)
    graph = prune_context(
        path,
        target,
        budget=budget,
        workspace=workspace,
        repo_key=repo_key,
    )
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
        contract_edges=[asdict(edge) for edge in graph.contract_edges],
        contract_endpoints=[asdict(endpoint) for endpoint in graph.contract_endpoints],
        contract_evidence_summary=_contract_evidence_summary(graph),
    )


def _contract_evidence_summary(graph: Any) -> dict[str, int]:
    summary: dict[str, int] = {}
    for edge in graph.contract_edges:
        summary[edge.evidence] = summary.get(edge.evidence, 0) + 1
    return summary


def index_contract_manifest(
    manifest_path: str | Path,
    *,
    db_path: str | Path,
    workspace: str | None = None,
    repo_key: str | None = None,
    project_root: str | None = None,
    default_evidence: str = "declared",
) -> ContractIndexResult:
    """Index an explicit contract manifest into v4 contract evidence tables."""
    snapshot, manifest_workspace, manifest_repo_key = contract_snapshot_from_manifest(
        manifest_path,
        db_path=db_path,
        workspace=workspace,
        project_root=project_root,
        default_evidence=default_evidence,
    )
    resolved_workspace = workspace or manifest_workspace
    resolved_repo_key = repo_key or manifest_repo_key
    index_run_id = IndexWriter(db_path).write_contract(
        snapshot,
        workspace=resolved_workspace,
        repo_key=resolved_repo_key,
    )
    return ContractIndexResult(
        index_run_id=index_run_id,
        db_path=str(Path(db_path)),
        manifest_path=str(Path(manifest_path)),
        workspace=resolved_workspace,
        repo_key=resolved_repo_key,
        endpoint_count=len(snapshot.endpoints),
        binding_count=sum(len(endpoint.bindings) for endpoint in snapshot.endpoints),
    )


def index_openapi_contract(
    openapi_path: str | Path,
    *,
    db_path: str | Path,
    service: str,
    version: str | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
    project_root: str | None = None,
) -> ContractIndexResult:
    """Index OpenAPI 3.x endpoints/schemas as contract facts without code bindings."""
    snapshot = openapi_snapshot_from_file(
        openapi_path,
        service=service,
        version=version,
        project_root=project_root,
    )
    resolved_repo_key = repo_key or f"{service}-openapi"
    index_run_id = IndexWriter(db_path).write_contract(
        snapshot,
        workspace=workspace,
        repo_key=resolved_repo_key,
    )
    return ContractIndexResult(
        index_run_id=index_run_id,
        db_path=str(Path(db_path)),
        manifest_path=str(Path(openapi_path)),
        workspace=workspace,
        repo_key=resolved_repo_key,
        endpoint_count=len(snapshot.endpoints),
        binding_count=0,
    )


def list_index_symbols(
    *,
    db_path: str | Path | None = None,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[dict[str, Any]]:
    """Return symbol records as JSON-serializable dicts."""
    path = resolve_db_path(db_path)
    records = list_symbols(
        path,
        query=query,
        kind=kind,
        limit=limit,
        index_run_id=index_run_id,
        workspace=workspace,
        repo_key=repo_key,
    )
    return [asdict(record) for record in records]


def list_contracts(
    *,
    db_path: str | Path | None = None,
    query: str | None = None,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[dict[str, Any]]:
    """Return contract endpoint records as JSON-serializable dicts."""
    path = resolve_db_path(db_path)
    endpoints = list_contract_endpoints(
        path,
        query=query,
        index_run_id=index_run_id,
        workspace=workspace,
        repo_key=repo_key,
    )
    return [asdict(endpoint) for endpoint in endpoints]


def get_workspace_info(
    *,
    db_path: str | Path | None = None,
    workspace: str,
) -> dict[str, Any]:
    """Return source-neutral workspace run summary."""
    path = resolve_db_path(db_path)
    summaries = workspace_run_summaries(path, workspace=workspace)
    code_repos = [item for item in summaries if item.run_kind == "code"]
    contract_sources = [item for item in summaries if item.run_kind == "contract"]
    return {
        "workspace": workspace,
        "repo_count": len(summaries),
        "code_repo_count": len(code_repos),
        "contract_source_count": len(contract_sources),
        "symbol_count": sum(item.symbol_count for item in summaries),
        "edge_count": sum(item.edge_count for item in summaries),
        "contract_endpoint_count": sum(
            item.contract_endpoint_count for item in summaries
        ),
        "contract_binding_count": sum(item.contract_binding_count for item in summaries),
        "runs": [asdict(item) for item in summaries],
    }


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
        "workspace": info.workspace,
        "repo_key": info.repo_key,
        "run_kind": info.run_kind,
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
    prune_mode: str = "smart",
    workspace: str | None = None,
    repo_key: str | None = None,
) -> dict[str, Any]:
    """Return compression KPI as a JSON-serializable dict."""
    path = resolve_db_path(db_path)
    budget = _budget(
        max_symbols=max_symbols,
        call_depth=call_depth,
        max_tokens=max_tokens,
        prune_mode=prune_mode,
    )
    weave_options = WeaveOptions(member_signatures=member_signatures, javadoc=javadoc)
    report = compute_compression(
        path,
        target,
        sources,
        budget=budget,
        format=format,
        options=weave_options,
        workspace=workspace,
        repo_key=repo_key,
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
