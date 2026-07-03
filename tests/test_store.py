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


def test_schema_version_is_v3_after_init(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    init_db(db)

    conn = sqlite3.connect(db)
    try:
        version = conn.execute("SELECT MAX(version) FROM meta_schema_version").fetchone()[0]
        assert version == 3
        symbol_columns = {row[1] for row in conn.execute("PRAGMA table_info(scip_symbol)")}
        run_columns = {row[1] for row in conn.execute("PRAGMA table_info(index_run)")}
        assert "relative_path" in symbol_columns
        assert "repo_id" in run_columns
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"workspace", "repo"} <= tables
    finally:
        conn.close()


def test_v1_database_migrates_to_v3(tmp_path: Path) -> None:
    from importlib import resources

    db = tmp_path / "symbols.db"
    v1_ref = resources.files("stubborn.store") / "schema" / "v1.sql"
    with resources.as_file(v1_ref) as v1_path:
        conn = sqlite3.connect(db)
        try:
            conn.executescript(v1_path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    IndexWriter(db).write(
        IndexSnapshot(
            scip_source="fixture.json",
            symbols=[SymbolRecord(stable_id="a", kind="class", relative_path="A.java")],
            edges=[],
        )
    )

    conn = sqlite3.connect(db)
    try:
        version = conn.execute("SELECT MAX(version) FROM meta_schema_version").fetchone()[0]
        assert version == 3
        row = conn.execute("SELECT relative_path FROM scip_symbol WHERE stable_id = 'a'").fetchone()
        assert row[0] == "A.java"
        columns = {row[1] for row in conn.execute("PRAGMA table_info(index_run)")}
        assert "repo_id" in columns
    finally:
        conn.close()


def test_merge_replaces_path_and_keeps_others(tmp_path: Path) -> None:
    from stubborn.ingest.scip import load_scip_index
    from stubborn.store.reader import list_symbols

    fixtures = Path(__file__).resolve().parents[1] / "examples" / "fixtures"
    base = load_scip_index(fixtures / "two_documents.json")
    updated = load_scip_index(fixtures / "two_documents_merged.json")

    db = tmp_path / "symbols.db"
    writer = IndexWriter(db)
    run_id = writer.write(base)
    assert run_id == 1

    writer.merge(updated, paths={"com/example/OrderService.java"})
    info = read_info(db)
    assert info.index_run_id == 1
    assert info.mode == "merged"
    assert info.merge_count == 1
    assert info.symbol_count == 4
    assert info.edge_count == 2

    names = {s.display_name for s in list_symbols(db, limit=50)}
    assert "PaymentService" in names
    assert "Order" in names
    assert "OrderService" in names

    assert _edge_kinds(db, "process", "Order") == {"signature-ref", "type"}


def test_merge_without_paths_uses_snapshot_documents(tmp_path: Path) -> None:
    from stubborn.ingest.scip import load_scip_index

    fixtures = Path(__file__).resolve().parents[1] / "examples" / "fixtures"
    base = load_scip_index(fixtures / "two_documents.json")
    updated = load_scip_index(fixtures / "two_documents_merged.json")

    db = tmp_path / "symbols.db"
    writer = IndexWriter(db)
    writer.write(base)
    writer.merge(updated)

    info = read_info(db)
    assert info.symbol_count == 4
    assert info.edge_count == 2
    assert info.merge_count == 1


def test_sequential_path_merges_preserve_cross_file_edges(tmp_path: Path) -> None:
    from stubborn.ingest.scip import load_scip_index

    fixtures = Path(__file__).resolve().parents[1] / "examples" / "fixtures"
    base = load_scip_index(fixtures / "two_documents.json")
    updated = load_scip_index(fixtures / "two_documents_merged.json")

    db = tmp_path / "symbols.db"
    writer = IndexWriter(db)
    writer.write(base)

    writer.merge(updated, paths={"com/example/OrderService.java"})
    first = read_info(db)
    assert first.edge_count == 2
    assert _edge_kinds(db, "process", "Order") == {"signature-ref", "type"}

    writer.merge(updated, paths={"com/example/Order.java"})
    second = read_info(db)
    assert second.edge_count == 2
    assert second.merge_count == 2
    assert _edge_kinds(db, "process", "Order") == {"signature-ref", "type"}


def test_workspace_context_crosses_repo_source_symbols(tmp_path: Path) -> None:
    from stubborn.config import ContextBudget
    from stubborn.graph.prune import prune_context
    from stubborn.store.reader import list_symbols

    db = tmp_path / "symbols.db"
    service = "semanticdb maven com/example/lib/Service#"
    helper = "semanticdb maven com/example/lib/Helper#"
    controller = "semanticdb maven com/example/app/Controller#"
    handle = "semanticdb maven com/example/app/Controller#handle()."

    repo_a = IndexSnapshot(
        scip_source="repo-a.json",
        project_root="/workspace/repo-a",
        language="java",
        symbols=[
            SymbolRecord(
                stable_id=controller,
                display_name="Controller",
                kind="class",
                signature="public class Controller",
                relative_path="src/Controller.java",
            ),
            SymbolRecord(
                stable_id=handle,
                display_name="handle",
                kind="method",
                signature="public void handle(Service service)",
                relative_path="src/Controller.java",
            ),
            SymbolRecord(
                stable_id=service,
                display_name="Service",
                kind="class",
                signature="public class Service",
            ),
        ],
        edges=[EdgeRecord(handle, service, "reference")],
    )
    repo_b = IndexSnapshot(
        scip_source="repo-b.json",
        project_root="/workspace/repo-b",
        language="java",
        symbols=[
            SymbolRecord(
                stable_id=service,
                display_name="Service",
                kind="class",
                signature="public class Service",
                relative_path="src/Service.java",
            ),
            SymbolRecord(
                stable_id=helper,
                display_name="Helper",
                kind="class",
                signature="public class Helper",
                relative_path="src/Helper.java",
            ),
        ],
        edges=[EdgeRecord(service, helper, "type")],
    )

    writer = IndexWriter(db)
    writer.write(repo_a, workspace="acme", repo_key="repo-a")
    writer.write(repo_b, workspace="acme", repo_key="repo-b")

    graph = prune_context(
        db,
        handle,
        workspace="acme",
        budget=ContextBudget(call_closure_depth=2, max_symbols=20),
    )
    names = {symbol.display_name for symbol in graph.symbols}
    assert {"handle", "Service", "Helper"} <= names

    reverse_graph = prune_context(
        db,
        service,
        workspace="acme",
        budget=ContextBudget(call_closure_depth=2, max_symbols=20),
    )
    reverse_names = {symbol.display_name for symbol in reverse_graph.symbols}
    assert {"handle", "Service", "Helper"} <= reverse_names

    listed = list_symbols(db, workspace="acme", query="Service", limit=10)
    assert [symbol.stable_id for symbol in listed].count(service) == 1


def _edge_kinds(db: Path, from_display: str, to_display: str) -> set[str]:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            """
            SELECT e.edge_kind
            FROM scip_edge e
            JOIN scip_symbol src ON src.id = e.from_symbol_id
            JOIN scip_symbol dst ON dst.id = e.to_symbol_id
            WHERE src.display_name = ?
              AND dst.display_name = ?
            """,
            (from_display, to_display),
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()
