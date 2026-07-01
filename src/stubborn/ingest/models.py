"""In-memory models for symbol index snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolRecord:
    stable_id: str
    display_name: str | None = None
    kind: str | None = None
    signature: str | None = None
    documentation: str | None = None


@dataclass(frozen=True)
class EdgeRecord:
    from_stable_id: str
    to_stable_id: str
    edge_kind: str = "reference"


@dataclass
class IndexSnapshot:
    scip_source: str
    symbols: list[SymbolRecord] = field(default_factory=list)
    edges: list[EdgeRecord] = field(default_factory=list)
    project_root: str | None = None
    scip_hash: str | None = None
    language: str | None = None
