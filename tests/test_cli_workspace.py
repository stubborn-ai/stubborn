"""Targeted CLI coverage for workspace and scoped command branches."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from stubborn.cli import app
from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord
from stubborn.store.writer import IndexWriter, read_info

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON = REPO_ROOT / "examples" / "fixtures" / "minimal.json"


def _latest_run_id(db: Path) -> int:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT id FROM index_run ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        return int(row[0])
    finally:
        conn.close()


def _project_root_for_run(db: Path, run_id: int) -> str | None:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT project_root FROM index_run WHERE id = ?",
            (run_id,),
        ).fetchone()
        assert row is not None
        return row[0]
    finally:
        conn.close()


def test_workspace_init_creates_schema(tmp_path: Path) -> None:
    db = tmp_path / "workspace.db"
    result = CliRunner().invoke(app, ["workspace", "init", "--db", str(db)])

    assert result.exit_code == 0, result.stdout + result.stderr
    assert db.is_file()

    conn = sqlite3.connect(db)
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()

    assert {"workspace", "repo", "index_run"} <= tables


def test_workspace_register_repo_persists_metadata(tmp_path: Path) -> None:
    db = tmp_path / "workspace.db"
    runner = CliRunner()

    first = runner.invoke(
        app,
        [
            "workspace",
            "register-repo",
            "--db",
            str(db),
            "--repo",
            "orders",
            "--workspace",
            "acme",
            "--root",
            "/workspace/orders",
            "--language",
            "java",
        ],
    )
    assert first.exit_code == 0, first.stdout + first.stderr

    second = runner.invoke(
        app,
        [
            "workspace",
            "register-repo",
            "--db",
            str(db),
            "--repo",
            "orders",
            "--workspace",
            "acme",
            "--language",
            "kotlin",
        ],
    )
    assert second.exit_code == 0, second.stdout + second.stderr

    conn = sqlite3.connect(db)
    try:
        workspace_row = conn.execute(
            "SELECT name FROM workspace WHERE name = 'acme'",
        ).fetchone()
        repo_row = conn.execute(
            """
            SELECT w.name, r.repo_key, r.root, r.language
            FROM repo r
            JOIN workspace w ON w.id = r.workspace_id
            WHERE r.repo_key = 'orders'
            """,
        ).fetchone()
    finally:
        conn.close()

    assert workspace_row == ("acme",)
    assert repo_row == ("acme", "orders", "/workspace/orders", "kotlin")


def test_info_run_id_selects_specific_run(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    writer = IndexWriter(db)
    first = writer.write(
        IndexSnapshot(
            scip_source="first.json",
            symbols=[
                SymbolRecord(
                    stable_id="semanticdb maven com/example/Foo#",
                    display_name="Foo",
                    kind="class",
                )
            ],
        ),
    )
    second = writer.write(
        IndexSnapshot(
            scip_source="second.json",
            symbols=[
                SymbolRecord(
                    stable_id="semanticdb maven com/example/Foo#",
                    display_name="Foo",
                    kind="class",
                ),
                SymbolRecord(
                    stable_id="semanticdb maven com/example/Foo#bar().",
                    display_name="bar",
                    kind="method",
                ),
            ],
            edges=[EdgeRecord("semanticdb maven com/example/Foo#bar().", "semanticdb maven com/example/Foo#", "reference")],
        ),
    )

    result = CliRunner().invoke(app, ["info", str(db), "--run-id", str(first)])

    assert result.exit_code == 0, result.stdout + result.stderr
    assert f"Index run:      {first}" in result.stdout
    assert "Symbols:        1" in result.stdout
    assert "Run kind:       code" in result.stdout
    assert _latest_run_id(db) == second


def test_info_workspace_rejects_run_id(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    IndexWriter(db).write(
        IndexSnapshot(
            scip_source="workspace.json",
            symbols=[
                SymbolRecord(
                    stable_id="semanticdb maven com/example/Foo#",
                    display_name="Foo",
                    kind="class",
                )
            ],
        ),
        workspace="acme",
        repo_key="orders",
    )

    result = CliRunner().invoke(
        app,
        ["info", str(db), "--workspace", "acme", "--run-id", "1"],
    )

    assert result.exit_code != 0
    assert "--workspace cannot be combined with --run-id" in (result.stdout + result.stderr)


def test_list_symbols_kind_filters(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    class_stable_id = "semanticdb maven com/example/Foo#"
    method_stable_id = "semanticdb maven com/example/Foo#bar()."
    IndexWriter(db).write(
        IndexSnapshot(
            scip_source="fixture.json",
            symbols=[
                SymbolRecord(
                    stable_id=class_stable_id,
                    display_name="Foo",
                    kind="class",
                ),
                SymbolRecord(
                    stable_id=method_stable_id,
                    display_name="bar",
                    kind="method",
                ),
            ],
        ),
    )

    class_result = CliRunner().invoke(app, ["list-symbols", str(db), "--kind", "class"])
    assert class_result.exit_code == 0, class_result.stdout + class_result.stderr
    assert class_result.stdout.splitlines() == [f"{class_stable_id}\tFoo\tclass"]

    method_result = CliRunner().invoke(app, ["list-symbols", str(db), "--kind", "method"])
    assert method_result.exit_code == 0, method_result.stdout + method_result.stderr
    assert method_result.stdout.splitlines() == [f"{method_stable_id}\tbar\tmethod"]


def test_index_project_root_is_persisted(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    result = CliRunner().invoke(
        app,
        [
            "index",
            "--scip",
            str(FIXTURE_JSON),
            "--out",
            str(db),
            "--project-root",
            "/workspace/demo",
        ],
    )

    assert result.exit_code == 0, result.stdout + result.stderr
    assert _project_root_for_run(db, _latest_run_id(db)) == "/workspace/demo"
    assert read_info(db).symbol_count > 0
