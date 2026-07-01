"""spring-petclinic scale-up neighbor coverage (optional — requires E2E index)."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context, get_metrics
from stubborn.store.reader import resolve_stable_id

EXAMPLE_ROOT = Path(__file__).resolve().parents[1] / "examples" / "spring-petclinic"
DB_PATH = EXAMPLE_ROOT / "metadata" / "symbols.db"
UPSTREAM_JAVA = EXAMPLE_ROOT / "upstream" / "src" / "main" / "java"
EXPECTED_PATH = EXAMPLE_ROOT / "metadata" / "expected-context-types-vet-controller.txt"

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="spring-petclinic symbols.db not built — run petclinic-e2e",
)


def test_vet_controller_includes_expected_types() -> None:
    target = resolve_stable_id(DB_PATH, display_name="VetController")
    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    result = get_context(target, db_path=DB_PATH)
    missing = [name for name in required if name not in result.text]
    assert not missing, f"missing from context: {missing}"


def test_vet_controller_compression_at_scale() -> None:
    if not UPSTREAM_JAVA.exists():
        pytest.skip("upstream clone not present for metrics")
    target = resolve_stable_id(DB_PATH, display_name="VetController")
    report = get_metrics(target, UPSTREAM_JAVA, db_path=DB_PATH)
    assert report["source_files"] >= 25
    assert report["token_savings_percent"] >= 70.0
    assert report["stub_symbols"] >= 10
