"""Tests for stubborn.api (CLI / SDK integration surface)."""

from __future__ import annotations

from pathlib import Path

import pytest

from stubborn.api import get_context, get_index_info, get_metrics, list_index_symbols
from stubborn.ingest.scip import load_scip_index
from stubborn.store.reader import list_symbols, resolve_db_path
from stubborn.store.writer import IndexWriter

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
TARGET = "semanticdb maven com/example/OrderService#process()."


def _write_source_fixture(tmp_path: Path) -> Path:
    source_root = tmp_path / "src" / "main" / "java" / "com" / "example"
    source_root.mkdir(parents=True)
    rules = "\n".join(
        f"                // business rule {i}: validate order state before returning context."
        for i in range(40)
    )
    (source_root / "OrderService.java").write_text(
        """
        package com.example;

        public class OrderService {
            public Order process(OrderRepository repository) {
                Order order = repository.findById("demo");
RULES
                repository.save(order);
                return order;
            }
        }
        """.replace("RULES", rules),
        encoding="utf-8",
    )
    (source_root / "OrderRepository.java").write_text(
        """
        package com.example;

        public interface OrderRepository {
            Order findById(String id);
            void save(Order order);
        }
        """,
        encoding="utf-8",
    )
    return tmp_path / "src" / "main" / "java"


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
    assert "documentation" in symbols[0]


def test_get_metrics_api(indexed_db: Path, tmp_path: Path) -> None:
    report = get_metrics(TARGET, _write_source_fixture(tmp_path), db_path=indexed_db)
    assert report["source_files"] == 2
    assert report["compression_ratio"] > 0.5
    assert "stub_text" in report
