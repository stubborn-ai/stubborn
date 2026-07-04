"""Pure snapshot enrichment helpers shared by JSON and SCIP ingest."""

from __future__ import annotations

import re

from stubborn.ingest.models import EdgeRecord, SymbolRecord

_SIGNATURE_TYPE_RE = re.compile(r"\b([A-Z][\w]*)\b")
_PRIMITIVE_OR_JDK_SKIP = frozenset(
    {
        "Boolean",
        "Byte",
        "Character",
        "Double",
        "Float",
        "Integer",
        "Long",
        "Number",
        "Object",
        "Optional",
        "Short",
        "String",
        "UUID",
        "Void",
    }
)


def is_scip_local_symbol(symbol: str) -> bool:
    return symbol.startswith("local ") or symbol.startswith("local/")


def _is_type_record(record: SymbolRecord) -> bool:
    kind = (record.kind or "").lower()
    if kind in ("class", "interface", "enum", "record"):
        return True
    if not record.stable_id.endswith("#"):
        return False
    return "." not in record.stable_id.split("#", 1)[-1]


def _build_type_name_index(symbols: dict[str, SymbolRecord]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for record in symbols.values():
        if not record.display_name or not _is_type_record(record):
            continue
        index.setdefault(record.display_name, []).append(record.stable_id)
    for stable_ids in index.values():
        stable_ids.sort(key=lambda sid: (not sid.endswith("#"), sid))
    return index


def _edges_from_signatures(symbols: dict[str, SymbolRecord]) -> list[EdgeRecord]:
    type_index = _build_type_name_index(symbols)
    edges: list[EdgeRecord] = []

    for record in symbols.values():
        if is_scip_local_symbol(record.stable_id):
            continue
        signature = (record.signature or "").strip()
        if not signature:
            continue

        seen_targets: set[str] = set()
        for match in _SIGNATURE_TYPE_RE.finditer(signature):
            type_name = match.group(1)
            if type_name in _PRIMITIVE_OR_JDK_SKIP:
                continue
            for target_id in type_index.get(type_name, []):
                if target_id == record.stable_id or target_id in seen_targets:
                    continue
                seen_targets.add(target_id)
                edges.append(EdgeRecord(record.stable_id, target_id, "signature-ref"))

    return edges


def _constructor_enclosing_type(constructor_stable_id: str) -> str | None:
    if "<init>" not in constructor_stable_id:
        return None
    return constructor_stable_id.split("#", 1)[0] + "#"


def _expand_constructor_type_edges(edges: list[EdgeRecord]) -> list[EdgeRecord]:
    extra: list[EdgeRecord] = []
    for edge in edges:
        type_id = _constructor_enclosing_type(edge.to_stable_id)
        if type_id is None or type_id == edge.to_stable_id:
            continue
        extra.append(EdgeRecord(edge.from_stable_id, type_id, "reference"))
    return extra


def _dedupe_edges(edges: list[EdgeRecord]) -> list[EdgeRecord]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[EdgeRecord] = []
    for edge in edges:
        key = (edge.from_stable_id, edge.to_stable_id, edge.edge_kind)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def enrich_snapshot_edges(
    symbols: list[SymbolRecord] | dict[str, SymbolRecord],
    edges: list[EdgeRecord],
) -> list[EdgeRecord]:
    """Add signature and constructor-derived reference edges, then dedupe."""
    if isinstance(symbols, dict):
        symbol_map = symbols
    else:
        symbol_map = {record.stable_id: record for record in symbols}
    enriched = [
        edge
        for edge in edges
        if not is_scip_local_symbol(edge.from_stable_id)
        and not is_scip_local_symbol(edge.to_stable_id)
    ]
    enriched.extend(_edges_from_signatures(symbol_map))
    enriched.extend(_expand_constructor_type_edges(enriched))
    return _dedupe_edges(enriched)
