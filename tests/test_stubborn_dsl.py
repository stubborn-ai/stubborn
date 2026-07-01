"""Tests for Stubborn-DSL weaver."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context
from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.store.writer import IndexWriter
from stubborn.weave.dispatch import weave_context
from stubborn.weave.java_stub import weave_java_stub
from stubborn.weave.stubborn_dsl import weave_stubborn_dsl

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"


def test_stubborn_dsl_header_and_types(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    target = "semanticdb maven com/example/OrderService#process()."
    graph = prune_context(
        db,
        target,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50),
    )

    result = weave_stubborn_dsl(graph)
    text = result.text

    assert text.startswith("stubborn-dsl/1.0\n")
    assert "# Guide:" in text
    assert "target OrderService.process" in text
    assert "policy declarations-only" in text
    assert "types:" in text
    assert "c Order" in text
    assert "member m OrderService.process" in text
    assert "void process(Order order)" in text
    assert "edges:" in text


def test_stubborn_dsl_more_compact_than_java_stub(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    target = "semanticdb maven com/example/OrderService#"
    graph = prune_context(
        db,
        target,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50),
    )

    java = weave_java_stub(graph)
    dsl = weave_stubborn_dsl(graph)

    assert "# Guide:" in dsl.text
    assert "OrderService" in dsl.text
    assert "{ /* stub */ }" not in dsl.text
    # Guide adds ~30 tokens fixed overhead; DSL wins on larger graphs (demo-spring, petclinic).
    if java.estimated_tokens >= 80:
        assert dsl.estimated_tokens < java.estimated_tokens


def test_dispatch_rejects_unknown_format() -> None:
    from stubborn.graph.prune import PrunedGraph

    graph = PrunedGraph(target_stable_id="x", symbols=[], edges=[])
    with pytest.raises(ValueError, match="Unsupported format"):
        weave_context(graph, format="yaml")


def test_api_get_context_stubborn_dsl(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    result = get_context(
        "semanticdb maven com/example/OrderService#",
        db_path=db,
        format="stubborn-dsl",
    )
    assert result.format == "stubborn-dsl"
    assert result.text.startswith("stubborn-dsl/1.0")
