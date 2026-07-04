"""Graph pruning for bounded LLM context."""

from __future__ import annotations

import re
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from stubborn.config import DEFAULT_CONTEXT_BUDGET, ContextBudget, apply_prune_mode
from stubborn.store.reader import latest_index_run_ids

_SIGNATURE_TYPE_RE = re.compile(r"\b([A-Z][\w]*)\b")
_INFERRED_EDGE_KINDS = frozenset({"signature-ref"})
_CONTRACT_EVIDENCE_RANK = {
    "strong": 0,
    "declared": 1,
    "inferred": 2,
    "unknown": 3,
}


@dataclass(frozen=True)
class PrunedSymbol:
    stable_id: str
    display_name: str | None
    kind: str | None
    signature: str | None
    documentation: str | None
    depth: int


@dataclass(frozen=True)
class ContractPrunedEdge:
    from_stable_id: str
    to_stable_id: str
    endpoint_stable_id: str
    endpoint_display_name: str | None
    protocol: str
    method_or_verb: str | None
    address: str
    from_role: str
    to_role: str
    evidence: str
    from_source: str | None
    to_source: str | None


@dataclass
class PrunedGraph:
    target_stable_id: str
    symbols: list[PrunedSymbol]
    edges: list[tuple[str, str, str]]
    contract_edges: list[ContractPrunedEdge] = field(default_factory=list)


def _should_exclude(stable_id: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in stable_id for pattern in patterns)


def _type_member_stable_ids(target_stable_id: str, stable_to_id: dict[str, int]) -> list[str]:
    """Fields, methods, and constructors owned by a type symbol (stable_id ends with #)."""
    if not target_stable_id.endswith("#"):
        return []
    return [
        stable_id
        for stable_id in stable_to_id
        if stable_id.startswith(target_stable_id) and stable_id != target_stable_id
    ]


def _best_symbol_row(rows: list[sqlite3.Row]) -> sqlite3.Row:
    """Prefer source-defined symbols over external leaves, then deterministic repo order."""
    return sorted(
        rows,
        key=lambda row: (
            row["relative_path"] is None,
            row["repo_priority"] if row["repo_priority"] is not None else 0,
            row["repo_key"] or "",
            -int(row["index_run_id"]),
            row["stable_id"],
        ),
    )[0]


def _build_type_name_index(symbols_by_id: dict[int, sqlite3.Row]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for symbol_id, row in symbols_by_id.items():
        name = row["display_name"]
        if not name:
            continue
        kind = (row["kind"] or "").lower()
        if kind in ("class", "interface", "enum", "record") or row["stable_id"].endswith("#"):
            index.setdefault(name, []).append(symbol_id)
    return index


def _signature_type_ref_ids(
    symbol_row: sqlite3.Row,
    type_name_index: dict[str, list[int]],
) -> list[int]:
    """Infer type symbol ids referenced in a field/method signature."""
    signature = (symbol_row["signature"] or "").strip()
    if not signature:
        return []

    refs: list[int] = []
    seen: set[int] = set()
    for match in _SIGNATURE_TYPE_RE.finditer(signature):
        for symbol_id in type_name_index.get(match.group(1), []):
            if symbol_id not in seen:
                seen.add(symbol_id)
                refs.append(symbol_id)
    return refs


def _depth_limit_for_edge(
    edge_kind: str,
    current_depth: int,
    budget: ContextBudget,
) -> bool:
    """Return True when neighbor at current_depth + 1 is within budget."""
    next_depth = current_depth + 1
    if edge_kind in ("type", "implementation"):
        limit = budget.type_closure_depth
        if limit is None:
            return True
        return next_depth <= limit

    limit = budget.call_closure_depth
    return next_depth <= limit


def _allowed_contract_evidence(budget: ContextBudget) -> frozenset[str]:
    if budget.prune_mode == "strict":
        return frozenset({"strong", "declared"})
    return frozenset({"strong", "declared", "inferred"})


def _weaker_contract_evidence(left: str, right: str) -> str:
    return max(
        (left, right),
        key=lambda evidence: _CONTRACT_EVIDENCE_RANK.get(evidence, 999),
    )


def _contract_run_ids(
    conn: sqlite3.Connection,
    *,
    workspace: str | None,
    repo_key: str | None,
) -> list[int]:
    try:
        return latest_index_run_ids(
            conn,
            workspace=workspace,
            repo_key=repo_key,
            run_kind="contract",
        )
    except ValueError:
        return []


def _build_contract_adjacency(
    conn: sqlite3.Connection,
    *,
    contract_run_ids: list[int],
    stable_to_id: dict[str, int],
    budget: ContextBudget,
) -> tuple[dict[int, list[tuple[int, ContractPrunedEdge]]], list[ContractPrunedEdge]]:
    if not contract_run_ids:
        return {}, []

    allowed_evidence = _allowed_contract_evidence(budget)
    placeholders = ",".join("?" * len(contract_run_ids))
    rows = conn.execute(
        f"""
        SELECT ce.stable_id AS endpoint_stable_id,
               ce.display_name AS endpoint_display_name,
               ce.protocol,
               ce.method_or_verb,
               ce.address,
               cb.code_stable_id,
               cb.role,
               cb.evidence,
               cb.source
        FROM contract_binding cb
        JOIN contract_endpoint ce ON ce.id = cb.endpoint_id
        WHERE ce.index_run_id IN ({placeholders})
        ORDER BY ce.stable_id, cb.role, cb.code_stable_id
        """,
        contract_run_ids,
    ).fetchall()

    endpoint_bindings: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        if row["evidence"] not in allowed_evidence:
            continue
        if row["code_stable_id"] not in stable_to_id:
            continue
        endpoint_bindings.setdefault(row["endpoint_stable_id"], []).append(row)

    adjacency: dict[int, list[tuple[int, ContractPrunedEdge]]] = {}
    contract_edges: list[ContractPrunedEdge] = []
    seen_edges: set[tuple[str, str, str, str, str]] = set()
    for bindings in endpoint_bindings.values():
        for from_binding in bindings:
            from_id = stable_to_id[from_binding["code_stable_id"]]
            for to_binding in bindings:
                if from_binding["code_stable_id"] == to_binding["code_stable_id"]:
                    continue
                if {from_binding["role"], to_binding["role"]} != {"provider", "consumer"}:
                    continue
                to_id = stable_to_id[to_binding["code_stable_id"]]
                evidence = _weaker_contract_evidence(
                    from_binding["evidence"],
                    to_binding["evidence"],
                )
                edge = ContractPrunedEdge(
                    from_stable_id=from_binding["code_stable_id"],
                    to_stable_id=to_binding["code_stable_id"],
                    endpoint_stable_id=from_binding["endpoint_stable_id"],
                    endpoint_display_name=from_binding["endpoint_display_name"],
                    protocol=from_binding["protocol"],
                    method_or_verb=from_binding["method_or_verb"],
                    address=from_binding["address"],
                    from_role=from_binding["role"],
                    to_role=to_binding["role"],
                    evidence=evidence,
                    from_source=from_binding["source"],
                    to_source=to_binding["source"],
                )
                key = (
                    edge.from_stable_id,
                    edge.to_stable_id,
                    edge.endpoint_stable_id,
                    edge.from_role,
                    edge.to_role,
                )
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                adjacency.setdefault(from_id, []).append((to_id, edge))
                contract_edges.append(edge)

    return adjacency, contract_edges


def _is_type_row(row: sqlite3.Row) -> bool:
    kind = (row["kind"] or "").lower()
    if kind in ("class", "interface", "enum", "record"):
        return True
    stable_id = row["stable_id"]
    if not stable_id.endswith("#"):
        return False
    member_suffix = stable_id.split("#", 1)[-1]
    return not member_suffix


def _enqueue_symbol(
    symbol_id: int,
    depth: int,
    *,
    seen: dict[int, int],
    queue: deque[int],
    budget: ContextBudget,
) -> None:
    if symbol_id in seen or len(seen) >= budget.max_symbols:
        return
    seen[symbol_id] = depth
    queue.append(symbol_id)


def prune_context(
    db_path: str | Path,
    target_stable_id: str,
    budget: ContextBudget | None = None,
    *,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> PrunedGraph:
    """BFS prune from target symbol using call/type edge kinds."""
    budget = apply_prune_mode(budget or DEFAULT_CONTEXT_BUDGET)
    use_heuristics = budget.use_signature_heuristics
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_ids = latest_index_run_ids(
            conn,
            index_run_id=index_run_id,
            workspace=workspace,
            repo_key=repo_key,
        )
        run_placeholders = ",".join("?" * len(run_ids))

        symbols_by_id: dict[int, sqlite3.Row] = {}
        stable_to_rows: dict[str, list[sqlite3.Row]] = {}
        for row in conn.execute(
            f"""
            SELECT s.id, s.index_run_id, s.stable_id, s.display_name, s.kind,
                   s.signature, s.documentation, s.relative_path,
                   r.repo_key, r.priority AS repo_priority
            FROM scip_symbol s
            JOIN index_run ir ON ir.id = s.index_run_id
            LEFT JOIN repo r ON r.id = ir.repo_id
            WHERE s.index_run_id IN ({run_placeholders})
            """,
            run_ids,
        ):
            symbols_by_id[row["id"]] = row
            stable_to_rows.setdefault(row["stable_id"], []).append(row)

        stable_to_id = {
            stable_id: int(_best_symbol_row(rows)["id"])
            for stable_id, rows in stable_to_rows.items()
        }

        if target_stable_id not in stable_to_id:
            raise ValueError(f"Symbol not found in index: {target_stable_id}")

        adjacency: dict[int, list[tuple[int, str]]] = {}
        for row in conn.execute(
            f"""
            SELECT from_symbol_id, to_symbol_id, edge_kind
            FROM scip_edge
            WHERE index_run_id IN ({run_placeholders})
            """,
            run_ids,
        ):
            from_row = symbols_by_id[row["from_symbol_id"]]
            to_row = symbols_by_id[row["to_symbol_id"]]
            from_id = stable_to_id[from_row["stable_id"]]
            to_id = stable_to_id[to_row["stable_id"]]
            adjacency.setdefault(from_id, []).append((to_id, row["edge_kind"]))
            adjacency.setdefault(to_id, []).append((from_id, row["edge_kind"]))

        contract_adjacency, all_contract_edges = _build_contract_adjacency(
            conn,
            contract_run_ids=_contract_run_ids(conn, workspace=workspace, repo_key=repo_key),
            stable_to_id=stable_to_id,
            budget=budget,
        )

        start_id = stable_to_id[target_stable_id]
        type_name_index = _build_type_name_index(symbols_by_id)
        seen: dict[int, int] = {}
        queue: deque[int] = deque()

        _enqueue_symbol(start_id, 0, seen=seen, queue=queue, budget=budget)
        for member_stable_id in _type_member_stable_ids(target_stable_id, stable_to_id):
            _enqueue_symbol(
                stable_to_id[member_stable_id],
                0,
                seen=seen,
                queue=queue,
                budget=budget,
            )

        while queue and len(seen) < budget.max_symbols:
            current_id = queue.popleft()
            current_depth = seen[current_id]
            current_row = symbols_by_id[current_id]

            if use_heuristics:
                signature_refs = _signature_type_ref_ids(current_row, type_name_index)
            else:
                signature_refs = []
            for ref_id in signature_refs:
                canonical_ref_id = stable_to_id[symbols_by_id[ref_id]["stable_id"]]
                if current_depth > 0:
                    continue
                if canonical_ref_id in seen:
                    continue
                ref_row = symbols_by_id[canonical_ref_id]
                if _should_exclude(ref_row["stable_id"], budget.exclude_patterns):
                    continue
                if not _depth_limit_for_edge("type", current_depth, budget):
                    continue
                _enqueue_symbol(
                    canonical_ref_id,
                    current_depth + 1,
                    seen=seen,
                    queue=queue,
                    budget=budget,
                )

            for neighbor_id, edge_kind in adjacency.get(current_id, []):
                if neighbor_id in seen:
                    continue

                if not use_heuristics and edge_kind in _INFERRED_EDGE_KINDS:
                    continue

                neighbor = symbols_by_id[neighbor_id]
                if _should_exclude(neighbor["stable_id"], budget.exclude_patterns):
                    continue

                if not _depth_limit_for_edge(edge_kind, current_depth, budget):
                    continue

                if current_depth >= 1 and not _is_type_row(neighbor):
                    continue

                _enqueue_symbol(
                    neighbor_id,
                    current_depth + 1,
                    seen=seen,
                    queue=queue,
                    budget=budget,
                )

            for neighbor_id, _contract_edge in contract_adjacency.get(current_id, []):
                if neighbor_id in seen:
                    continue

                neighbor = symbols_by_id[neighbor_id]
                if _should_exclude(neighbor["stable_id"], budget.exclude_patterns):
                    continue

                if not _depth_limit_for_edge("reference", current_depth, budget):
                    continue

                _enqueue_symbol(
                    neighbor_id,
                    current_depth + 1,
                    seen=seen,
                    queue=queue,
                    budget=budget,
                )

        pruned_symbols: list[PrunedSymbol] = []
        for symbol_id, depth in sorted(seen.items(), key=lambda item: item[1]):
            row = symbols_by_id[symbol_id]
            pruned_symbols.append(
                PrunedSymbol(
                    stable_id=row["stable_id"],
                    display_name=row["display_name"],
                    kind=row["kind"],
                    signature=row["signature"],
                    documentation=row["documentation"],
                    depth=depth,
                )
            )

        stable_ids = {s.stable_id for s in pruned_symbols}
        pruned_edges: list[tuple[str, str, str]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for row in conn.execute(
            f"""
            SELECT fs.stable_id, ts.stable_id, e.edge_kind
            FROM scip_edge e
            JOIN scip_symbol fs ON fs.id = e.from_symbol_id
            JOIN scip_symbol ts ON ts.id = e.to_symbol_id
            WHERE e.index_run_id IN ({run_placeholders})
            """,
            run_ids,
        ):
            edge = (row[0], row[1], row[2])
            if row[0] in stable_ids and row[1] in stable_ids and edge not in seen_edges:
                seen_edges.add(edge)
                pruned_edges.append(edge)

        pruned_contract_edges: list[ContractPrunedEdge] = []
        seen_contract_edges: set[tuple[str, str, str, str, str]] = set()
        for edge in all_contract_edges:
            key = (
                edge.from_stable_id,
                edge.to_stable_id,
                edge.endpoint_stable_id,
                edge.from_role,
                edge.to_role,
            )
            if key in seen_contract_edges:
                continue
            if edge.from_stable_id not in stable_ids or edge.to_stable_id not in stable_ids:
                continue
            seen_contract_edges.add(key)
            pruned_contract_edges.append(edge)

        return PrunedGraph(
            target_stable_id=target_stable_id,
            symbols=pruned_symbols,
            edges=pruned_edges,
            contract_edges=pruned_contract_edges,
        )
    finally:
        conn.close()
