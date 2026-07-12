"""Tests for stubborn doctor (ADR-015)."""

from __future__ import annotations

import json
import sqlite3
from importlib import resources
from pathlib import Path

from typer.testing import CliRunner

from stubborn.cli import app
from stubborn.doctor.models import DOCTOR_REPORT_SCHEMA, PACKAGE_ID
from stubborn.doctor.run import run_doctor
from stubborn.store.writer import read_info, read_schema_version

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON = REPO_ROOT / "examples" / "fixtures" / "minimal.json"


def _table_names(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _legacy_v1_db(root: Path) -> Path:
    db = root / "symbols.db"
    v1_ref = resources.files("stubborn.store") / "schema" / "v1.sql"
    with resources.as_file(v1_ref) as v1_path:
        conn = sqlite3.connect(db)
        try:
            conn.executescript(v1_path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO index_run (scip_source, tool_version) VALUES (?, ?)",
                ("fixture.json", "0.0.0"),
            )
            run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                "INSERT INTO scip_symbol (index_run_id, stable_id, kind) VALUES (?, ?, ?)",
                (run_id, "semanticdb maven com/example/Foo#", "class"),
            )
            conn.commit()
        finally:
            conn.close()
    return db


def test_doctor_empty_project_warns_without_db(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, fix_hint=False)
    assert report.exit_code() == 2
    assert any(check.id == "db.present" and check.status == "warn" for check in report.checks)
    assert any(check.id == "core.import" and check.status == "pass" for check in report.checks)


def test_doctor_json_schema(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, fix_hint=False)
    payload = report.to_dict()
    assert payload["schema"] == DOCTOR_REPORT_SCHEMA
    assert payload["package"] == PACKAGE_ID
    assert payload["command"] == "stubborn doctor"
    assert payload["exit"] == report.exit_code()
    assert isinstance(payload["checks"], list)


def test_doctor_with_indexed_db_passes(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "metadata" / "symbols.db"
    index = runner.invoke(
        app,
        ["index", "--scip", str(FIXTURE_JSON), "--out", str(db)],
    )
    assert index.exit_code == 0, index.stdout + index.stderr

    report = run_doctor(tmp_path, fix_hint=False)
    assert report.exit_code() == 0
    assert any(check.id == "db.present" and check.status == "pass" for check in report.checks)
    assert any(check.id == "db.index_run" and check.status == "pass" for check in report.checks)


def test_doctor_missing_explicit_db_fails(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, db_path=tmp_path / "missing.db", fix_hint=False)
    assert report.exit_code() == 1
    assert any(check.id == "db.present" and check.status == "fail" for check in report.checks)


def test_doctor_detects_build_signal(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    report = run_doctor(tmp_path, fix_hint=False)
    assert any(check.id == "project.signal.build" for check in report.checks)


def test_doctor_journey_hints_java_without_scip(tmp_path: Path) -> None:
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
    report = run_doctor(tmp_path, fix_hint=True)
    assert any(
        check.id == "journey.java_index" and check.status == "warn" for check in report.checks
    )
    assert any(check.id == "journey.docs" for check in report.checks)


def test_cli_doctor_json(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"
    runner.invoke(app, ["index", "--scip", str(FIXTURE_JSON), "--out", str(db)])
    result = runner.invoke(app, ["doctor", str(tmp_path), "--json", "--no-fix-hint"])
    assert result.exit_code == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == DOCTOR_REPORT_SCHEMA
    assert payload["exit"] == 0


def test_cli_help_lists_doctor() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout


def test_doctor_does_not_migrate_legacy_schema(tmp_path: Path) -> None:
    _legacy_v1_db(tmp_path)
    tables_before = _table_names(tmp_path / "symbols.db")
    version_before = read_schema_version(tmp_path / "symbols.db")
    assert version_before == 1

    report = run_doctor(tmp_path, fix_hint=False)

    version_after = read_schema_version(tmp_path / "symbols.db")
    tables_after = _table_names(tmp_path / "symbols.db")
    assert version_after == version_before == 1
    assert tables_before == tables_after
    assert "workspace" not in tables_after

    schema_check = next(check for check in report.checks if check.id == "db.schema")
    assert schema_check.status == "warn"
    assert any(check.id == "db.index_run" and check.status == "pass" for check in report.checks)


def test_read_info_migrate_false_leaves_legacy_schema_unchanged(tmp_path: Path) -> None:
    db = _legacy_v1_db(tmp_path)
    version_before = read_schema_version(db)

    info = read_info(db, migrate=False)

    assert read_schema_version(db) == version_before == 1
    assert info.symbol_count == 1
    assert info.mode == "snapshot"
    assert info.run_kind == "code"
