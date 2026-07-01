"""Tests for graph pruning and weaving."""

from __future__ import annotations

from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.store.writer import IndexWriter
from stubborn.weave.java_stub import weave_java_stub

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"


def test_prune_and_weave_e2e(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    snapshot = load_scip_index(FIXTURE)
    IndexWriter(db).write(snapshot)

    target = "semanticdb maven com/example/OrderService#process()."
    graph = prune_context(
        db,
        target,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50),
    )

    assert len(graph.symbols) >= 2
    assert graph.target_stable_id == target

    result = weave_java_stub(graph)
    text = result.text
    assert "OrderService" in text
    assert "method bodies" in text.lower() or "stub" in text.lower()
    assert "{" not in text or "/* stub */" in text
