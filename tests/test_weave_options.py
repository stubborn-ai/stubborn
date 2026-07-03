"""Tests for weave granularity options (member signatures, Javadoc)."""

from __future__ import annotations

import pytest

from stubborn.graph.prune import PrunedGraph, PrunedSymbol
from stubborn.weave.java_stub import weave_java_stub
from stubborn.weave.members import (
    format_java_javadoc_prefix,
    javadoc_lines,
    type_includes_method_signatures,
)
from stubborn.weave.options import DEFAULT_WEAVE_OPTIONS, WeaveOptions
from stubborn.weave.stubborn_dsl import weave_stubborn_dsl

TARGET_TYPE = "semanticdb maven com/example/OrderService#"
NEIGHBOR_TYPE = "semanticdb maven com/example/OrderRepository#"


def _sample_graph() -> PrunedGraph:
    symbols = [
        PrunedSymbol(
            stable_id=TARGET_TYPE,
            display_name="OrderService",
            kind="class",
            signature="public class OrderService",
            documentation="/** Handles orders.\n * @param id order id\n */",
            depth=0,
        ),
        PrunedSymbol(
            stable_id=f"{TARGET_TYPE}create().",
            display_name="create",
            kind="method",
            signature="public Order create()",
            documentation=None,
            depth=0,
        ),
        PrunedSymbol(
            stable_id=NEIGHBOR_TYPE,
            display_name="OrderRepository",
            kind="interface",
            signature="public interface OrderRepository",
            documentation="/** Persistence port. */",
            depth=1,
        ),
        PrunedSymbol(
            stable_id=f"{NEIGHBOR_TYPE}findById().",
            display_name="findById",
            kind="method",
            signature="public Optional<Order> findById(String id)",
            documentation=None,
            depth=1,
        ),
    ]
    return PrunedGraph(
        target_stable_id=TARGET_TYPE,
        symbols=symbols,
        edges=[],
    )


def test_weave_options_defaults() -> None:
    options = DEFAULT_WEAVE_OPTIONS
    assert options.member_signatures == "target"
    assert options.javadoc is None
    assert options.effective_javadoc("java-stub") == "summary"
    assert options.effective_javadoc("stubborn-dsl") == "off"


def test_weave_options_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="member_signatures"):
        WeaveOptions(member_signatures="bogus")
    with pytest.raises(ValueError, match="javadoc"):
        WeaveOptions(javadoc="bogus")


def test_type_includes_method_signatures_modes() -> None:
    selected = {TARGET_TYPE, NEIGHBOR_TYPE}
    assert type_includes_method_signatures(
        TARGET_TYPE,
        target_type_id=TARGET_TYPE,
        mode="target",
        selected_type_ids=selected,
    )
    assert not type_includes_method_signatures(
        NEIGHBOR_TYPE,
        target_type_id=TARGET_TYPE,
        mode="target",
        selected_type_ids=selected,
    )
    assert type_includes_method_signatures(
        NEIGHBOR_TYPE,
        target_type_id=TARGET_TYPE,
        mode="neighbors",
        selected_type_ids=selected,
    )
    assert not type_includes_method_signatures(
        TARGET_TYPE,
        target_type_id=TARGET_TYPE,
        mode="neighbors",
        selected_type_ids=selected,
    )


def test_javadoc_summary_vs_full() -> None:
    doc = "/** Summary line.\n * @param id uuid\n * @return ok\n */"
    assert javadoc_lines(doc, "summary") == ["Summary line."]
    full = javadoc_lines(doc, "full")
    assert "Summary line." in full
    assert any("@param" in line for line in full)


def test_java_stub_member_signatures_target_only() -> None:
    graph = _sample_graph()
    result = weave_java_stub(graph, options=WeaveOptions(member_signatures="target"))
    assert "create()" in result.text
    assert "findById(String id)" not in result.text


def test_java_stub_member_signatures_neighbors() -> None:
    graph = _sample_graph()
    result = weave_java_stub(graph, options=WeaveOptions(member_signatures="neighbors"))
    assert "create()" not in result.text
    assert "findById(String id)" in result.text


def test_java_stub_member_signatures_off() -> None:
    graph = _sample_graph()
    result = weave_java_stub(graph, options=WeaveOptions(member_signatures="off"))
    assert "create()" not in result.text
    assert "/* stub */" in result.text


def test_java_stub_javadoc_off() -> None:
    graph = _sample_graph()
    result = weave_java_stub(
        graph,
        options=WeaveOptions(member_signatures="off", javadoc="off"),
    )
    assert "Handles orders" not in result.text
    assert format_java_javadoc_prefix(graph.symbols[0].documentation, "off") == ""


def test_java_stub_javadoc_full() -> None:
    graph = _sample_graph()
    result = weave_java_stub(
        graph,
        options=WeaveOptions(member_signatures="off", javadoc="full"),
    )
    assert "// Handles orders." in result.text
    assert "// @param id order id" in result.text


def test_stubborn_dsl_member_signatures_all() -> None:
    graph = _sample_graph()
    result = weave_stubborn_dsl(graph, options=WeaveOptions(member_signatures="all"))
    assert "m OrderService.create" in result.text
    assert "m OrderRepository.findById" in result.text


def test_stubborn_dsl_javadoc_summary_when_explicit() -> None:
    graph = _sample_graph()
    result = weave_stubborn_dsl(
        graph,
        options=WeaveOptions(member_signatures="off", javadoc="summary"),
    )
    assert 'doc "Handles orders."' in result.text
    assert "members:" not in result.text
