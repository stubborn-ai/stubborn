"""Tests for SQLite symbol graph store."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord
from stubborn.store.writer import IndexWriter, init_db, read_info


def test_init_db_creates_schema(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    init_db(db)

    conn = sqlite3.connect(db)
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
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


def test_signature_ref_edges_persist_in_sqlite(tmp_path: Path) -> None:
    """Regression: signature-ref must survive CHECK constraint + INSERT (not OR IGNORE)."""
    from stubborn.ingest.scip import load_scip_index

    db = tmp_path / "symbols.db"
    snapshot = load_scip_index(
        Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
    )
    in_memory = sum(1 for e in snapshot.edges if e.edge_kind == "signature-ref")
    assert in_memory >= 1

    IndexWriter(db).write(snapshot)

    conn = sqlite3.connect(db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM scip_edge WHERE edge_kind = 'signature-ref'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert count == in_memory
    assert count >= 1


def test_list_symbols_includes_documentation(tmp_path: Path) -> None:
    from stubborn.ingest.scip import load_scip_index
    from stubborn.store.reader import list_symbols

    db = tmp_path / "symbols.db"
    fixture = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "minimal.json"
    IndexWriter(db).write(load_scip_index(fixture))

    symbols = list_symbols(db, query="OrderService", limit=5)
    assert symbols
    assert hasattr(symbols[0], "documentation")
    # fixture may omit docs; field must be present (None or str)
    assert symbols[0].documentation is None or isinstance(symbols[0].documentation, str)


def test_invalid_edge_kind_raises_on_write(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    snapshot = IndexSnapshot(
        scip_source="fixture.json",
        symbols=[
            SymbolRecord(stable_id="a", kind="class"),
            SymbolRecord(stable_id="b", kind="class"),
        ],
        edges=[EdgeRecord(from_stable_id="a", to_stable_id="b", edge_kind="not-a-real-kind")],
    )

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        IndexWriter(db).write(snapshot)
