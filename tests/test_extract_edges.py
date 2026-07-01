"""Tests for SCIP edge extraction (signatures, occurrences, constructors)."""

from __future__ import annotations

from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.extract import parsed_index_to_snapshot
from stubborn.ingest.scip import load_scip_index
from stubborn.ingest.stream import parse_index_bytes
from stubborn.store.writer import IndexWriter
from stubborn.weave.java_stub import weave_java_stub

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
DEMO_SCIP = Path(__file__).resolve().parents[1] / "examples" / "demo-spring" / "index.scip"
ORDER_SERVICE = (
    "semanticdb maven maven/com.example/orders-demo 0.1.0-SNAPSHOT "
    "com/example/orders/service/OrderService#"
)


def _edge_pairs(snapshot) -> set[tuple[str, str, str]]:
    return {(e.from_stable_id, e.to_stable_id, e.edge_kind) for e in snapshot.edges}


def test_signature_edges_add_return_and_parameter_types() -> None:
    snapshot = load_scip_index(FIXTURE)
    pairs = _edge_pairs(snapshot)
    find_by_id = "semanticdb maven com/example/OrderRepository#findById()."
    order = "semanticdb maven com/example/Order#"
    assert (find_by_id, order, "reference") in pairs


def test_occurrences_skip_local_enclosing_for_constructor_refs() -> None:
    if not DEMO_SCIP.exists():
        return

    parsed = parse_index_bytes(DEMO_SCIP.read_bytes())
    snapshot = parsed_index_to_snapshot(
        parsed,
        scip_source=str(DEMO_SCIP),
        scip_hash=None,
    )
    get_order = next(
        s.stable_id
        for s in snapshot.symbols
        if s.display_name == "getOrder" and "OrderService" in s.stable_id
    )
    onf_type = next(
        s.stable_id
        for s in snapshot.symbols
        if s.display_name == "OrderNotFoundException" and s.stable_id.endswith("#")
    )
    pairs = _edge_pairs(snapshot)
    assert any(
        from_id == get_order and to_id == onf_type and kind == "reference"
        for from_id, to_id, kind in pairs
    ), "getOrder should reference OrderNotFoundException type"
    assert not any(from_id.startswith("local ") for from_id, _, _ in pairs)


def test_order_service_context_includes_order_not_found_exception(tmp_path: Path) -> None:
    if not DEMO_SCIP.exists():
        return

    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(DEMO_SCIP))
    graph = prune_context(
        db,
        ORDER_SERVICE,
        budget=ContextBudget(call_closure_depth=2, max_symbols=100),
    )
    woven = weave_java_stub(graph)
    assert "OrderNotFoundException" in woven.text
