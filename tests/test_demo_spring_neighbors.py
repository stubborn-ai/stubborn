"""demo-spring neighbor coverage for OrderService context."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context, get_metrics

DEMO_ROOT = Path(__file__).resolve().parents[1] / "examples" / "demo-spring"
DB_PATH = DEMO_ROOT / "metadata" / "symbols.db"
JAVA_ROOT = DEMO_ROOT / "src" / "main" / "java"
EXPECTED_PATH = DEMO_ROOT / "metadata" / "expected-context-types.txt"
TARGET = (
    "semanticdb maven maven/com.example/orders-demo 0.1.0-SNAPSHOT "
    "com/example/orders/service/OrderService#"
)


pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="demo-spring symbols.db not built — run E2E first",
)


def test_order_service_includes_expected_types() -> None:
    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = get_context(TARGET, db_path=DB_PATH)
    missing = [name for name in required if name not in result.text]
    assert not missing, f"missing from context: {missing}"


def test_order_service_compression_still_strong() -> None:
    report = get_metrics(TARGET, JAVA_ROOT, db_path=DB_PATH)
    assert report["token_savings_percent"] >= 75.0
    assert report["stub_symbols"] >= 8
