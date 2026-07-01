"""Tests for token estimation and budget trimming."""

from __future__ import annotations

from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import PrunedGraph, PrunedSymbol
from stubborn.metrics import collect_source_stats, compute_compression
from stubborn.store.writer import IndexWriter
from stubborn.ingest.scip import load_scip_index
from stubborn.tokens import estimate_tokens
from stubborn.weave.java_stub import weave_java_stub

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
DEMO_JAVA = (
    Path(__file__).resolve().parents[1] / "examples" / "demo-spring" / "src" / "main" / "java"
)


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 8) == 2


def test_weave_respects_max_tokens() -> None:
    symbols = [
        PrunedSymbol("a", "A", "class", "public class A", None, 0),
        PrunedSymbol("b", "B", "class", "public class B", None, 1),
        PrunedSymbol("c", "C", "class", "public class C", None, 2),
    ]
    graph = PrunedGraph(target_stable_id="a", symbols=symbols, edges=[])
    result = weave_java_stub(graph, max_tokens=40)
    assert result.symbol_count <= 2
    assert result.dropped_for_budget >= 1
    assert result.estimated_tokens <= 40 or result.symbol_count == 1


def test_weave_skips_constructors_when_type_present() -> None:
    symbols = [
        PrunedSymbol(
            "semanticdb maven com/example/Foo#",
            "Foo",
            "class",
            "public class Foo",
            None,
            0,
        ),
        PrunedSymbol(
            "semanticdb maven com/example/Foo#`<init>`().",
            "<init>",
            "constructor",
            "public Foo();",
            None,
            0,
        ),
    ]
    graph = PrunedGraph(target_stable_id=symbols[0].stable_id, symbols=symbols, edges=[])
    result = weave_java_stub(graph)
    assert "public Foo();" not in result.text
    assert "public class Foo" in result.text


def test_metrics_on_fixture(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))
    report = compute_compression(
        db,
        "semanticdb maven com/example/OrderService#",
        DEMO_JAVA,
        budget=ContextBudget(max_tokens=12_000),
    )
    assert report.source.file_count >= 10
    assert report.stub.estimated_tokens > 0
    assert report.compression_ratio > 0.5
