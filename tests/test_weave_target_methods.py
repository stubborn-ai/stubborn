"""Tests for target-type method signatures in weavers (v0.9)."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context

DEMO_ROOT = Path(__file__).resolve().parents[1] / "examples" / "demo-spring"
DB_PATH = DEMO_ROOT / "metadata" / "symbols.db"
TARGET = (
    "semanticdb maven maven/com.example/orders-demo 0.1.0-SNAPSHOT "
    "com/example/orders/service/OrderService#"
)


pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="demo-spring symbols.db not built — run E2E first",
)


def test_order_service_type_includes_method_signatures() -> None:
    result = get_context(TARGET, db_path=DB_PATH)
    text = result.text
    assert "public class OrderService" in text
    assert "payOrder(UUID id)" in text
    assert "createOrder(CreateOrderRequest request)" in text
    assert "cancelOrder(UUID id)" in text


def test_order_service_stubborn_dsl_includes_members_block() -> None:
    result = get_context(TARGET, db_path=DB_PATH, format="stubborn-dsl")
    assert "members:" in result.text
    assert "m OrderService.payOrder" in result.text
