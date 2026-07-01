"""Smoke tests for Typer CLI commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from stubborn.cli import app

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SCIP = REPO_ROOT / "examples" / "fixtures" / "minimal.scip"
FIXTURE_JSON = REPO_ROOT / "examples" / "fixtures" / "minimal.json"
ORDER_SERVICE_TARGET = "semanticdb maven com/example/OrderService#"


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "index" in result.stdout
    assert "context" in result.stdout


def test_cli_index_info_and_context_scip(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"

    index = runner.invoke(
        app,
        ["index", "--scip", str(FIXTURE_SCIP), "--out", str(db)],
    )
    assert index.exit_code == 0, index.stdout + index.stderr
    assert db.is_file()

    info = runner.invoke(app, ["info", str(db)])
    assert info.exit_code == 0, info.stdout + info.stderr
    assert "Symbols" in info.stdout

    out = tmp_path / "order-service.stub.java"
    context = runner.invoke(
        app,
        [
            "context",
            str(db),
            "--target",
            ORDER_SERVICE_TARGET,
            "--out",
            str(out),
        ],
    )
    assert context.exit_code == 0, context.stdout + context.stderr
    assert out.is_file()
    assert "OrderService" in out.read_text(encoding="utf-8")


def test_cli_index_json_fixture(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"

    result = runner.invoke(
        app,
        ["index", "--scip", str(FIXTURE_JSON), "--out", str(db)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert db.is_file()
