"""Tests for API layer and MCP tool wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context, get_index_info, get_metrics, list_index_symbols
from stubborn.ingest.scip import load_scip_index
from stubborn.store.reader import list_symbols, resolve_db_path
from stubborn.store.writer import IndexWriter

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
DEMO_JAVA = (
    Path(__file__).resolve().parents[1] / "examples" / "demo-spring" / "src" / "main" / "java"
)
TARGET = "semanticdb maven com/example/OrderService#process()."


@pytest.fixture()
def indexed_db(tmp_path: Path) -> Path:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(load_scip_index(FIXTURE))
    return db


def test_resolve_db_path_from_argument(indexed_db: Path) -> None:
    assert resolve_db_path(indexed_db) == indexed_db


def test_resolve_db_path_from_env(indexed_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUBBORN_DB", str(indexed_db))
    assert resolve_db_path(None) == indexed_db


def test_resolve_db_path_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STUBBORN_DB", raising=False)
    with pytest.raises(ValueError, match="db_path is required"):
        resolve_db_path(None)


def test_list_symbols_filter(indexed_db: Path) -> None:
    all_symbols = list_symbols(indexed_db, limit=100)
    assert len(all_symbols) >= 2

    filtered = list_symbols(indexed_db, query="OrderService", limit=10)
    assert filtered
    assert all("OrderService" in s.stable_id or s.display_name == "OrderService" for s in filtered)


def test_get_context_api(indexed_db: Path) -> None:
    result = get_context(TARGET, db_path=indexed_db)
    assert result.target_stable_id == TARGET
    assert "OrderService" in result.text
    assert result.symbol_count >= 1
    assert result.estimated_tokens > 0


def test_get_index_info_api(indexed_db: Path) -> None:
    info = get_index_info(db_path=indexed_db)
    assert info["symbol_count"] >= 2
    assert info["index_run_id"] == 1
    assert str(indexed_db) in info["db_path"]


def test_list_index_symbols_api(indexed_db: Path) -> None:
    symbols = list_index_symbols(db_path=indexed_db, query="Order", limit=5)
    assert symbols
    assert "stable_id" in symbols[0]


def test_get_metrics_api(indexed_db: Path) -> None:
    report = get_metrics(TARGET, DEMO_JAVA, db_path=indexed_db)
    assert report["source_files"] >= 10
    assert report["compression_ratio"] > 0.5
    assert "stub_text" in report


def test_mcp_tools_callable(indexed_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("mcp")
    monkeypatch.setenv("STUBBORN_DB", str(indexed_db))

    from stubborn.mcp_server.server import get_context as mcp_get_context
    from stubborn.mcp_server.server import list_symbols as mcp_list_symbols
    from stubborn.mcp_server.server import metrics as mcp_metrics

    ctx = mcp_get_context(TARGET)
    assert ctx["text"]
    assert ctx["symbol_count"] >= 1

    listing = mcp_list_symbols(query="Order")
    assert listing["returned"] >= 1
    assert listing["symbols"]

    kpi = mcp_metrics(TARGET, str(DEMO_JAVA), include_stub_text=False)
    assert "stub_text" not in kpi
    assert kpi["token_savings_percent"] > 0
