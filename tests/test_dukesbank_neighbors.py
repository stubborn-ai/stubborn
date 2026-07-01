"""Duke's Bank neighbor coverage (optional — requires external index)."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context
from stubborn.store.reader import resolve_stable_id

EXAMPLE_ROOT = Path(__file__).resolve().parents[1] / "examples" / "dukesbank"
DB_PATH = EXAMPLE_ROOT / "metadata" / "symbols.db"

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason="dukesbank symbols.db not built — run examples/dukesbank E2E first",
)


def test_account_controller_includes_expected_neighbors() -> None:
    target = resolve_stable_id(DB_PATH, display_name="AccountControllerBean", prefer_type=True)
    result = get_context(target, db_path=DB_PATH)
    for name in ("LocalAccount", "LocalCustomer", "AccountDetails", "SessionBean"):
        assert name in result.text
