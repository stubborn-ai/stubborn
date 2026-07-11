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


def test_cli_index_bundled_fixture(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"

    result = runner.invoke(
        app,
        ["index", "--fixture", "minimal", "--out", str(db)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert db.is_file()

    info = runner.invoke(app, ["info", str(db)])
    assert info.exit_code == 0, info.stdout + info.stderr
    assert "Symbols" in info.stdout


def test_cli_fixture_path() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["fixture-path", "minimal"])
    assert result.exit_code == 0, result.stdout + result.stderr
    path = Path(result.stdout.strip())
    assert path.is_file()
    assert path.name == "minimal.json"


def test_cli_fixtures_list() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["fixtures"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "minimal" in result.stdout


def test_cli_index_merge(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"
    fixtures = REPO_ROOT / "examples" / "fixtures"

    base = runner.invoke(
        app,
        ["index", "--scip", str(fixtures / "two_documents.json"), "--out", str(db)],
    )
    assert base.exit_code == 0, base.stdout + base.stderr

    merged = runner.invoke(
        app,
        [
            "index",
            "--scip",
            str(fixtures / "two_documents_merged.json"),
            "--out",
            str(db),
            "--merge",
            "--paths",
            "com/example/OrderService.java",
        ],
    )
    assert merged.exit_code == 0, merged.stdout + merged.stderr
    assert "mode=merged" in merged.stdout

    info = runner.invoke(app, ["info", str(db)])
    assert info.exit_code == 0
    assert "Mode:           merged" in info.stdout


def test_cli_workspace_scope(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "symbols.db"

    index = runner.invoke(
        app,
        [
            "index",
            "--scip",
            str(FIXTURE_JSON),
            "--out",
            str(db),
            "--workspace",
            "acme",
            "--repo",
            "orders",
        ],
    )
    assert index.exit_code == 0, index.stdout + index.stderr

    info = runner.invoke(app, ["info", str(db)])
    assert info.exit_code == 0, info.stdout + info.stderr
    assert "Workspace:      acme" in info.stdout
    assert "Repo:           orders" in info.stdout

    workspace_info = runner.invoke(app, ["info", str(db), "--workspace", "acme"])
    assert workspace_info.exit_code == 0, workspace_info.stdout + workspace_info.stderr
    assert "Repos:          1" in workspace_info.stdout
    assert "- orders:" in workspace_info.stdout

    listed = runner.invoke(
        app,
        ["list-symbols", str(db), "--workspace", "acme", "--query", "OrderService"],
    )
    assert listed.exit_code == 0, listed.stdout + listed.stderr
    assert "OrderService" in listed.stdout
