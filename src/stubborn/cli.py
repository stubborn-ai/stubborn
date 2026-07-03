"""CLI entry point for Stubborn."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from stubborn.config import ContextBudget, apply_prune_mode, normalize_prune_mode
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.metrics import compute_compression
from stubborn.reconcile.diff import format_report, reconcile
from stubborn.reconcile.entities import SymbolEntity
from stubborn.store.writer import IndexWriter, init_db, read_info
from stubborn.weave.dispatch import weave_context
from stubborn.weave.options import WeaveOptions

app = typer.Typer(
    name="stubborn",
    help="Deterministic code context from symbol graphs — not vector search.",
    no_args_is_help=True,
)


@app.command("init-db")
def init_db_cmd(
    out: Path = typer.Option(..., "--out", "-o", help="SQLite file path to initialize"),
) -> None:
    """Initialize an empty symbol graph database (DDL only)."""
    init_db(out)
    typer.echo(f"Initialized {out}")


@app.command("index")
def index_cmd(
    scip: Path = typer.Option(
        ..., "--scip", help="SCIP index (.scip, .scip.ndjson, or .json fixture)"
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output SQLite file path"),
    project_root: Optional[str] = typer.Option(
        None,
        "--project-root",
        help="Optional project root path recorded in index_run",
    ),
) -> None:
    """Ingest a SCIP index into a local symbol graph SQLite database."""
    snapshot = load_scip_index(scip, project_root=project_root)
    writer = IndexWriter(out)
    index_run_id = writer.write(snapshot)
    typer.echo(
        f"Indexed {len(snapshot.symbols)} symbol(s), "
        f"{len(snapshot.edges)} edge(s) -> {out} (index_run_id={index_run_id})"
    )


@app.command("info")
def info_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    run_id: Optional[int] = typer.Option(
        None,
        "--run-id",
        help="Specific index_run id (default: latest)",
    ),
) -> None:
    """Show summary for an index run."""
    info = read_info(db_path, index_run_id=run_id)
    typer.echo(f"Index run:      {info.index_run_id}")
    typer.echo(f"SCIP source:    {info.scip_source}")
    typer.echo(f"Language:       {info.language or '(unknown)'}")
    typer.echo(f"Indexed at:     {info.indexed_at}")
    typer.echo(f"Symbols:        {info.symbol_count}")
    typer.echo(f"Edges:          {info.edge_count}")


@app.command("context")
def context_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    target: str = typer.Option(..., "--target", "-t", help="Target SCIP symbol stable_id"),
    format: str = typer.Option(
        "java-stub",
        "--format",
        "-f",
        help="Output format: java-stub | stubborn-dsl",
    ),
    max_symbols: int = typer.Option(200, "--max-symbols", help="Hard cap on pruned symbols"),
    call_depth: int = typer.Option(2, "--call-depth", help="Call/reference closure depth"),
    max_tokens: int = typer.Option(
        12_000,
        "--max-tokens",
        help="Hard cap on estimated output tokens (chars/4 heuristic)",
    ),
    member_signatures: str = typer.Option(
        "target",
        "--member-signatures",
        help="Method signatures on types: off | target | neighbors | all",
    ),
    javadoc: Optional[str] = typer.Option(
        None,
        "--javadoc",
        help="Javadoc in output: off | summary | full (default: summary for java-stub, off for stubborn-dsl)",
    ),
    prune_mode: str = typer.Option(
        "smart",
        "--prune-mode",
        help="Neighbor expansion: smart (SCIP + signature heuristics) | strict (SCIP edges only) | fast (smaller neighborhood)",
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Write context text to file (default: stdout)",
    ),
) -> None:
    """Prune the symbol graph and emit type-safe LLM context text."""
    try:
        normalize_prune_mode(prune_mode)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    budget = apply_prune_mode(
        ContextBudget(
            call_closure_depth=call_depth,
            max_symbols=max_symbols,
            max_tokens=max_tokens,
            prune_mode=prune_mode,
        )
    )
    graph = prune_context(db_path, target, budget=budget)

    try:
        weave_options = WeaveOptions(member_signatures=member_signatures, javadoc=javadoc)
        result = weave_context(
            graph,
            format=format,
            max_tokens=budget.max_tokens,
            options=weave_options,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    text = result.text

    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(
            f"Wrote {result.symbol_count} symbol(s) to {out} "
            f"(~{result.estimated_tokens} tokens, dropped={result.dropped_for_budget})"
        )
    else:
        typer.echo(text, nl=False)


@app.command("metrics")
def metrics_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    target: str = typer.Option(..., "--target", "-t", help="Target SCIP symbol stable_id"),
    sources: Path = typer.Option(
        ...,
        "--sources",
        "-s",
        help="Java source root for baseline size (e.g. src/main/java)",
    ),
    max_symbols: int = typer.Option(200, "--max-symbols"),
    call_depth: int = typer.Option(2, "--call-depth"),
    max_tokens: int = typer.Option(12_000, "--max-tokens"),
    member_signatures: str = typer.Option(
        "target",
        "--member-signatures",
        help="Method signatures on types: off | target | neighbors | all",
    ),
    javadoc: Optional[str] = typer.Option(
        None,
        "--javadoc",
        help="Javadoc in output: off | summary | full",
    ),
    prune_mode: str = typer.Option(
        "smart",
        "--prune-mode",
        help="Neighbor expansion: smart | strict | fast",
    ),
    stub_out: Optional[Path] = typer.Option(
        None,
        "--stub-out",
        "-o",
        help="Optional path to write stub text",
    ),
) -> None:
    """Compare pruned stub size against full Java sources (compression KPI)."""
    try:
        normalize_prune_mode(prune_mode)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    budget = apply_prune_mode(
        ContextBudget(
            call_closure_depth=call_depth,
            max_symbols=max_symbols,
            max_tokens=max_tokens,
            prune_mode=prune_mode,
        )
    )
    report = compute_compression(
        db_path,
        target,
        sources,
        budget=budget,
        options=WeaveOptions(member_signatures=member_signatures, javadoc=javadoc),
    )
    if stub_out:
        stub_out.write_text(report.stub.text, encoding="utf-8")
    typer.echo(report.format_summary())


@app.command("diff")
def diff_cmd(
    expected_db: Path = typer.Argument(..., help="Baseline SQLite index (ground truth)"),
    actual_db: Path = typer.Argument(..., help="Candidate SQLite index to compare"),
    in_scope: Optional[Path] = typer.Option(
        None,
        "--in-scope",
        help="Newline-separated stable_id list; only these symbols are required",
    ),
) -> None:
    """Reconcile symbol sets between two indexes (e.g. before/after migration)."""
    import sqlite3

    def _load_symbols(db: Path) -> set[SymbolEntity]:
        conn = sqlite3.connect(db)
        try:
            run_id = conn.execute("SELECT id FROM index_run ORDER BY id DESC LIMIT 1").fetchone()
            if run_id is None:
                return set()
            rows = conn.execute(
                "SELECT stable_id FROM scip_symbol WHERE index_run_id = ?",
                (run_id[0],),
            )
            return {SymbolEntity(row[0]) for row in rows}
        finally:
            conn.close()

    expected = _load_symbols(expected_db)
    actual = _load_symbols(actual_db)

    if in_scope:
        scope = {
            line.strip()
            for line in in_scope.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        expected = {e for e in expected if e.stable_id in scope}

    report = reconcile(expected, actual)
    typer.echo(format_report(report))
    if not report.ok:
        raise typer.Exit(code=1)

