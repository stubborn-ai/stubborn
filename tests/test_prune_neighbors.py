"""Tests for type-neighbor graph pruning."""

from __future__ import annotations

from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.store.writer import IndexWriter
from stubborn.weave.java_stub import weave_java_stub

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"


def test_method_target_prunes_without_member_noise(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    target = "semanticdb maven com/example/OrderService#process()."
    graph = prune_context(
        db,
        target,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50),
    )
    woven = weave_java_stub(graph)
    assert "OrderService" in woven.text
    assert woven.symbol_count >= 2
    assert "public class" in woven.text
    assert "customerEmail" not in woven.text
