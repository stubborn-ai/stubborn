"""Filter and path helpers for index snapshots."""

from __future__ import annotations

from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord


def snapshot_document_paths(snapshot: IndexSnapshot) -> set[str]:
    """Return non-empty relative_path values present on symbols."""
    return {path for path in (s.relative_path for s in snapshot.symbols) if path}


def resolve_merge_paths(snapshot: IndexSnapshot, paths: set[str] | None) -> set[str]:
    """Paths touched by a merge operation."""
    if paths is not None:
        return {path for path in paths if path}
    return snapshot_document_paths(snapshot)


def filter_snapshot_by_paths(snapshot: IndexSnapshot, paths: set[str]) -> IndexSnapshot:
    """Keep symbols (and internal edges) for the given document paths."""
    if not paths:
        return IndexSnapshot(
            scip_source=snapshot.scip_source,
            symbols=[],
            edges=[],
            project_root=snapshot.project_root,
            scip_hash=snapshot.scip_hash,
            language=snapshot.language,
        )

    symbols: list[SymbolRecord] = [s for s in snapshot.symbols if s.relative_path in paths]
    stable_ids = {s.stable_id for s in symbols}
    edges: list[EdgeRecord] = [
        edge
        for edge in snapshot.edges
        if edge.from_stable_id in stable_ids and edge.to_stable_id in stable_ids
    ]
    return IndexSnapshot(
        scip_source=snapshot.scip_source,
        symbols=symbols,
        edges=edges,
        project_root=snapshot.project_root,
        scip_hash=snapshot.scip_hash,
        language=snapshot.language,
    )
