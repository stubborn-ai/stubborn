"""Tests for SCIP edge extraction (signatures, occurrences, constructors)."""

from __future__ import annotations

from pathlib import Path

from stubborn.ingest.scip import load_scip_index

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"


def _edge_pairs(snapshot) -> set[tuple[str, str, str]]:
    return {(e.from_stable_id, e.to_stable_id, e.edge_kind) for e in snapshot.edges}


def test_signature_edges_add_return_and_parameter_types() -> None:
    snapshot = load_scip_index(FIXTURE)
    pairs = _edge_pairs(snapshot)
    find_by_id = "semanticdb maven com/example/OrderRepository#findById()."
    order = "semanticdb maven com/example/Order#"
    assert (find_by_id, order, "signature-ref") in pairs
