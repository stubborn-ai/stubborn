"""Graph pruning for bounded LLM context."""

from __future__ import annotations

import re
import sqlite3
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from stubborn.config import DEFAULT_CONTEXT_BUDGET, ContextBudget, apply_prune_mode
from stubborn.store.reader import latest_index_run_ids

_SIGNATURE_TYPE_RE = re.compile(r"\b([A-Z][\w]*)\b")
_INFERRED_EDGE_KINDS = frozenset({"signature-ref"})


@dataclass(frozen=True)
class PrunedSymbol:
    stable_id: str
    display_name: str | None
    kind: str | None
    signature: str | None
    documentation: str | None
    depth: int


@dataclass
class PrunedGraph:
    target_stable_id: str
    symbols: list[PrunedSymbol]
    edges: list[tuple[str, str, str]]


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
            adjacency.setdefault(row["from_symbol_id"], []).append(
                (row["to_symbol_id"], row["edge_kind"])
            )
            adjacency.setdefault(row["to_symbol_id"], []).append(
                (row["from_symbol_id"], row["edge_kind"])
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

            for ref_id in _signature_type_ref_ids(current_row, type_name_index):
                ref_row = symbols_by_id[ref_id]
                canonical_ref_id = stable_to_id[ref_row["stable_id"]]
                if not use_heuristics:
                    continue
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
                neighbor_row = symbols_by_id[neighbor_id]
                canonical_neighbor_id = stable_to_id[neighbor_row["stable_id"]]
                if canonical_neighbor_id in seen:
                    continue

                if not use_heuristics and edge_kind in _INFERRED_EDGE_KINDS:
                    continue

                neighbor = symbols_by_id[canonical_neighbor_id]
                if _should_exclude(neighbor["stable_id"], budget.exclude_patterns):
                    continue

                if not _depth_limit_for_edge(edge_kind, current_depth, budget):
                    continue

                if current_depth >= 1 and not _is_type_row(neighbor):
                    continue

                _enqueue_symbol(
                    canonical_neighbor_id,
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

        return PrunedGraph(
            target_stable_id=target_stable_id,
            symbols=pruned_symbols,
            edges=pruned_edges,
        )
    finally:
        conn.close()
