"""Tests for SQLite symbol graph store."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord
from stubborn.store.writer import IndexWriter, init_db, read_info


def test_init_db_creates_schema(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    init_db(db)

    conn = sqlite3.connect(db)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "index_run" in tables
        assert "scip_symbol" in tables
        assert "scip_edge" in tables
    finally:
        conn.close()


def test_write_and_read_info(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    snapshot = IndexSnapshot(
        scip_source="fixture.json",
        language="java",
        symbols=[
            SymbolRecord(
                stable_id="semanticdb maven com/example/Foo#",
                display_name="Foo",
                kind="class",
                signature="public class Foo",
            )
        ],
        edges=[],
    )

    writer = IndexWriter(db)
    run_id = writer.write(snapshot)
    info = read_info(db, index_run_id=run_id)

    assert info.index_run_id == run_id
    assert info.symbol_count == 1
    assert info.edge_count == 0
    assert info.language == "java"


def test_write_edges(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    snapshot = IndexSnapshot(
        scip_source="fixture.json",
        symbols=[
            SymbolRecord(stable_id="a", kind="class"),
            SymbolRecord(stable_id="b", kind="class"),
        ],
        edges=[EdgeRecord(from_stable_id="a", to_stable_id="b", edge_kind="reference")],
    )

    IndexWriter(db).write(snapshot)
    info = read_info(db)
    assert info.edge_count == 1
