"""Tests for stubborn doctor (ADR-015)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from stubborn.cli import app
from stubborn.doctor.models import DOCTOR_REPORT_SCHEMA, PACKAGE_ID
from stubborn.doctor.run import run_doctor

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_JSON = REPO_ROOT / "examples" / "fixtures" / "minimal.json"


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
