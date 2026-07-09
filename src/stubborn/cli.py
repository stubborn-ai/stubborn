"""CLI entry point for Stubborn."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from stubborn.api import index_contract_manifest, index_openapi_contract
from stubborn.config import ContextBudget, apply_prune_mode, normalize_prune_mode
from stubborn.doctor.report import format_json, format_text
from stubborn.doctor.run import run_doctor
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.metrics import compute_compression
from stubborn.reconcile.diff import format_report, reconcile
from stubborn.reconcile.entities import SymbolEntity
from stubborn.store.reader import list_contract_endpoints, list_symbols, workspace_run_summaries
from stubborn.store.writer import IndexWriter, init_db, read_info, register_repo
from stubborn.weave.dispatch import weave_context
from stubborn.weave.options import WeaveOptions

app = typer.Typer(
    name="stubborn",
    help="Deterministic code context from symbol graphs — not vector search.",
    no_args_is_help=True,
)
workspace_app = typer.Typer(help="Manage multi-repo workspace metadata.")
app.add_typer(workspace_app, name="workspace")


@workspace_app.command("init")
def workspace_init_cmd(
    db_path: Path = typer.Option(..., "--db", help="SQLite symbol graph file path"),
) -> None:
    """Initialize a workspace-capable symbol graph database."""
    init_db(db_path)
    typer.echo(f"Initialized workspace database {db_path}")


@workspace_app.command("register-repo")
def workspace_register_repo_cmd(
    db_path: Path = typer.Option(..., "--db", help="SQLite symbol graph file path"),
    repo: str = typer.Option(..., "--repo", help="Stable repo key inside the workspace"),
    workspace: str = typer.Option("default", "--workspace", help="Workspace name"),
    root: Optional[str] = typer.Option(None, "--root", help="Repo root path"),
    language: Optional[str] = typer.Option(None, "--language", help="Primary language"),
) -> None:
    """Register or update a repo entry without indexing."""
    repo_id = register_repo(
        db_path,
        repo_key=repo,
        workspace=workspace,
        root=root,
        language=language,
    )
    typer.echo(f"Registered repo {repo!r} in workspace {workspace!r} (repo_id={repo_id})")


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
    merge: bool = typer.Option(
        False,
        "--merge",
        help="Merge into the latest index run (path-scoped replace) instead of a new snapshot",
    ),
    paths: Optional[str] = typer.Option(
        None,
        "--paths",
        help="Comma-separated relative_path values to merge (default: all paths in SCIP)",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name for multi-repo indexing",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Repo key for multi-repo indexing; merge updates latest run for this repo",
    ),
) -> None:
    """Ingest a SCIP index into a local symbol graph SQLite database."""
    snapshot = load_scip_index(scip, project_root=project_root)
    writer = IndexWriter(out)
    path_set: set[str] | None = None
    if paths:
        path_set = {part.strip() for part in paths.split(",") if part.strip()}

    if merge:
        index_run_id = writer.merge(
            snapshot,
            paths=path_set,
            workspace=workspace,
            repo_key=repo,
        )
        info = read_info(out, index_run_id=index_run_id)
        typer.echo(
            f"Merged {len(snapshot.symbols)} input symbol(s), "
            f"{len(snapshot.edges)} input edge(s) -> {out} "
            f"(index_run_id={index_run_id}, stored_symbols={info.symbol_count}, "
            f"stored_edges={info.edge_count}, mode={info.mode}, merge_count={info.merge_count})"
        )
    else:
        if path_set is not None:
            raise typer.BadParameter("--paths requires --merge")
        index_run_id = writer.write(snapshot, workspace=workspace, repo_key=repo)
        typer.echo(
            f"Indexed {len(snapshot.symbols)} symbol(s), "
            f"{len(snapshot.edges)} edge(s) -> {out} "
            f"(index_run_id={index_run_id}, mode=snapshot)"
        )


@app.command("index-contract")
def index_contract_cmd(
    manifest: Path = typer.Option(
        ...,
        "--manifest",
        help="Explicit contract manifest (JSON-compatible YAML)",
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output SQLite file path"),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name; defaults to manifest workspace",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Contract source repo key; defaults to manifest contract_repo/bridge_repo",
    ),
    project_root: Optional[str] = typer.Option(
        None,
        "--project-root",
        help="Optional contract source root recorded in index_run",
    ),
    default_evidence: str = typer.Option(
        "declared",
        "--default-evidence",
        help="Evidence for bindings that do not specify one; default: declared",
    ),
) -> None:
    """Ingest an explicit contract manifest into v4 contract evidence tables."""
    try:
        result = index_contract_manifest(
            manifest,
            db_path=out,
            workspace=workspace,
            repo_key=repo,
            project_root=project_root,
            default_evidence=default_evidence,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Indexed {result.endpoint_count} contract endpoint(s), "
        f"{result.binding_count} binding(s) -> {out} "
        f"(index_run_id={result.index_run_id}, run_kind=contract)"
    )


@app.command("index-openapi")
def index_openapi_cmd(
    openapi: Path = typer.Option(
        ...,
        "--openapi",
        help="OpenAPI 3.x YAML/JSON document",
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output SQLite file path"),
    service: str = typer.Option(
        ...,
        "--service",
        help="Service name used in endpoint stable IDs",
    ),
    version: Optional[str] = typer.Option(
        None,
        "--version",
        help="Contract version; defaults to info.version or v1",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name for contract source tracking",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Contract source repo key; defaults to <service>-openapi",
    ),
    project_root: Optional[str] = typer.Option(
        None,
        "--project-root",
        help="Optional OpenAPI source root recorded in index_run",
    ),
) -> None:
    """Ingest OpenAPI 3.x endpoints/schemas without inferring code bindings."""
    try:
        result = index_openapi_contract(
            openapi,
            db_path=out,
            service=service,
            version=version,
            workspace=workspace,
            repo_key=repo,
            project_root=project_root,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Indexed {result.endpoint_count} OpenAPI endpoint(s), "
        f"{result.binding_count} binding(s) -> {out} "
        f"(index_run_id={result.index_run_id}, run_kind=contract)"
    )


@app.command("info")
def info_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    run_id: Optional[int] = typer.Option(
        None,
        "--run-id",
        help="Specific index_run id (default: latest)",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Show latest-run summary for every repo in a workspace",
    ),
) -> None:
    """Show summary for an index run."""
    if workspace is not None:
        if run_id is not None:
            raise typer.BadParameter("--workspace cannot be combined with --run-id")
        summaries = workspace_run_summaries(db_path, workspace=workspace)
        code_repos = [item for item in summaries if item.run_kind == "code"]
        contract_sources = [item for item in summaries if item.run_kind == "contract"]
        typer.echo(f"Workspace:      {workspace}")
        typer.echo(f"Repos:          {len(summaries)}")
        typer.echo(f"Code repos:     {len(code_repos)}")
        typer.echo(f"Contract sources: {len(contract_sources)}")
        typer.echo(f"Symbols:        {sum(item.symbol_count for item in summaries)}")
        typer.echo(f"Edges:          {sum(item.edge_count for item in summaries)}")
        typer.echo(f"Contract endpoints: {sum(item.contract_endpoint_count for item in summaries)}")
        typer.echo(f"Contract bindings:  {sum(item.contract_binding_count for item in summaries)}")
        for item in summaries:
            typer.echo(
                f"- {item.repo_key}: kind={item.run_kind}, run={item.index_run_id}, "
                f"symbols={item.symbol_count}, edges={item.edge_count}, "
                f"contract_endpoints={item.contract_endpoint_count}, "
                f"contract_bindings={item.contract_binding_count}, "
                f"mode={item.mode}, merges={item.merge_count}"
            )
        return

    info = read_info(db_path, index_run_id=run_id)
    typer.echo(f"Index run:      {info.index_run_id}")
    typer.echo(f"SCIP source:    {info.scip_source}")
    typer.echo(f"Language:       {info.language or '(unknown)'}")
    typer.echo(f"Indexed at:     {info.indexed_at}")
    typer.echo(f"Symbols:        {info.symbol_count}")
    typer.echo(f"Edges:          {info.edge_count}")
    typer.echo(f"Mode:           {info.mode}")
    typer.echo(f"Run kind:       {info.run_kind}")
    if info.workspace:
        typer.echo(f"Workspace:      {info.workspace}")
    if info.repo_key:
        typer.echo(f"Repo:           {info.repo_key}")
    if info.merge_count:
        typer.echo(f"Merge count:    {info.merge_count}")


@app.command("list-contracts")
def list_contracts_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Filter by endpoint stable_id, display name, or address",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name; list latest contract sources in that workspace",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Contract source repo key",
    ),
    run_id: Optional[int] = typer.Option(
        None,
        "--run-id",
        help="Specific contract index_run id",
    ),
    show_schema: bool = typer.Option(
        False,
        "--show-schema",
        help="Print schema constraints below each endpoint",
    ),
) -> None:
    """List contract endpoint stable IDs."""
    endpoints = list_contract_endpoints(
        db_path,
        query=query,
        index_run_id=run_id,
        workspace=workspace,
        repo_key=repo,
    )
    for endpoint in endpoints:
        verb = endpoint.method_or_verb or endpoint.protocol
        typer.echo(f"{endpoint.stable_id}\t{verb}\t{endpoint.address}")
        if show_schema:
            for constraint in endpoint.schema_constraints:
                required = (
                    ""
                    if constraint.required is None
                    else " required"
                    if constraint.required
                    else " optional"
                )
                type_name = constraint.type_name or "unknown"
                typer.echo(
                    f"  {constraint.location}.{constraint.field_path}: {type_name}{required}"
                )


@app.command("context")
def context_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    target: str = typer.Option(
        ...,
        "--target",
        "-t",
        help="Target code symbol or contract endpoint stable_id",
    ),
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
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name; query latest run for every repo in that workspace",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Repo key; query latest run for one repo",
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
    graph = prune_context(
        db_path,
        target,
        budget=budget,
        workspace=workspace,
        repo_key=repo,
    )

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
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name; query latest run for every repo in that workspace",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Repo key; query latest run for one repo",
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
        workspace=workspace,
        repo_key=repo,
    )
    if stub_out:
        stub_out.write_text(report.stub.text, encoding="utf-8")
    typer.echo(report.format_summary())


@app.command("list-symbols")
def list_symbols_cmd(
    db_path: Path = typer.Argument(..., help="SQLite symbol graph file path"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Name/signature filter"),
    kind: Optional[str] = typer.Option(None, "--kind", help="Symbol kind filter"),
    limit: int = typer.Option(50, "--limit", help="Maximum symbols to print"),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name; query latest run for every repo in that workspace",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="Repo key; query latest run for one repo",
    ),
) -> None:
    """List symbols from a legacy, repo, or workspace view."""
    for symbol in list_symbols(
        db_path,
        query=query,
        kind=kind,
        limit=limit,
        workspace=workspace,
        repo_key=repo,
    ):
        name = symbol.display_name or "(anonymous)"
        kind_text = symbol.kind or "(unknown)"
        typer.echo(f"{symbol.stable_id}\t{name}\t{kind_text}")


@app.command("doctor")
def doctor_cmd(
    path: Path = typer.Argument(
        Path("."),
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Project root to inspect",
    ),
    db: Optional[Path] = typer.Option(
        None,
        "--db",
        help="SQLite symbol graph to check (default: discover metadata/symbols.db)",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Workspace name for multi-repo summary checks",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit Doctor Report v1 JSON"),
    fix_hint: bool = typer.Option(
        True,
        "--fix-hint/--no-fix-hint",
        help="Include copy-paste hints in human output",
    ),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Suppress output; exit code only"),
) -> None:
    """Diagnose stubborn-stub readiness and symbol graph health (read-only).

    Does not invoke scip-java, start MCP, or auto-select index sources.
    See ADR-015 for custody scope; use sibling package doctors for MCP/watch.
    """
    report = run_doctor(path, db_path=db, workspace=workspace, fix_hint=fix_hint)
    if not quiet:
        if json_output:
            typer.echo(format_json(report))
        else:
            typer.echo(format_text(report, fix_hint=fix_hint))
    raise typer.Exit(code=report.exit_code())


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
