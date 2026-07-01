"""demo-spring neighbor coverage for OrderController context."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context, get_metrics
from stubborn.store.reader import resolve_stable_id

DEMO_ROOT = Path(__file__).resolve().parents[1] / "examples" / "demo-spring"
DB_PATH = DEMO_ROOT / "metadata" / "symbols.db"
JAVA_ROOT = DEMO_ROOT / "src" / "main" / "java"
EXPECTED_PATH = DEMO_ROOT / "metadata" / "expected-context-types-controller.txt"


pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="demo-spring symbols.db not built — run E2E first",
)


def _target() -> str:
    return resolve_stable_id(DB_PATH, display_name="OrderController")


def test_order_controller_includes_expected_types() -> None:
    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = get_context(_target(), db_path=DB_PATH)
    missing = [name for name in required if name not in result.text]
    assert not missing, f"missing from context: {missing}"


def test_order_controller_compression_still_strong() -> None:
    report = get_metrics(_target(), JAVA_ROOT, db_path=DB_PATH)
    assert report["token_savings_percent"] >= 75.0
    assert report["stub_symbols"] >= 5
