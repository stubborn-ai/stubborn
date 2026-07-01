"""Tests for prune_mode: smart, strict, fast."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.config import ContextBudget, apply_prune_mode, normalize_prune_mode
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.store.writer import IndexWriter

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
FIND_BY_ID = "semanticdb maven com/example/OrderRepository#findById()."
ORDER_SERVICE = "semanticdb maven com/example/OrderService#"


def test_normalize_prune_mode_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="prune_mode"):
        normalize_prune_mode("turbo")


def test_strict_omits_signature_heuristic_neighbors(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    smart = prune_context(
        db,
        FIND_BY_ID,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50, prune_mode="smart"),
    )
    strict = prune_context(
        db,
        FIND_BY_ID,
        budget=ContextBudget(call_closure_depth=2, max_symbols=50, prune_mode="strict"),
    )

    smart_ids = {s.stable_id for s in smart.symbols}
    strict_ids = {s.stable_id for s in strict.symbols}

    assert "semanticdb maven com/example/Order#" in smart_ids
    assert "semanticdb maven com/example/Order#" not in strict_ids
    assert FIND_BY_ID in strict_ids


def test_fast_neighborhood_smaller_than_smart_on_type_target(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    smart = prune_context(
        db,
        ORDER_SERVICE,
        budget=ContextBudget(call_closure_depth=2, max_symbols=200, prune_mode="smart"),
    )
    fast = prune_context(
        db,
        ORDER_SERVICE,
        budget=ContextBudget(call_closure_depth=2, max_symbols=200, prune_mode="fast"),
    )

    assert len(fast.symbols) <= len(smart.symbols)


def test_apply_prune_mode_caps_fast_limits() -> None:
    budget = apply_prune_mode(
        ContextBudget(call_closure_depth=5, max_symbols=500, prune_mode="fast")
    )
    assert budget.call_closure_depth == 1
    assert budget.max_symbols == 80
    assert budget.type_closure_depth == 1


def test_get_context_strict_via_api(tmp_path: Path) -> None:
    from stubborn.api import get_context

    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))

    result = get_context(FIND_BY_ID, db_path=db, prune_mode="strict")
    assert "findById" in result.text or "OrderRepository" in result.text
    assert "public class Order {" not in result.text
    assert "public class OrderService" in result.text
