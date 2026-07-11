"""Doctor checks for stubborn-stub custody (ADR-015)."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from stubborn import __version__
from stubborn.doctor.models import Check
from stubborn.doctor.signals import ProjectSignal, discover_project_signals
from stubborn.store.reader import list_contract_bindings, workspace_run_summaries
from stubborn.store.writer import read_info, read_schema_version

_SCIP_EXTRA_HINT = (
    "Install binary SCIP support with: pip install 'stubborn-stub[scip]' (stubborn-stub package)"
)


def runtime_checks() -> list[Check]:
    checks: list[Check] = []
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        checks.append(
            Check(
                id="runtime.python",
                status="fail",
                message=f"Python {major}.{minor} is below the required 3.11+",
                hint="Upgrade Python to 3.11 or newer (stubborn-stub)",
            )
        )
    else:
        checks.append(
            Check(
                id="runtime.python",
                status="pass",
                message=f"Python {major}.{minor}",
            )
        )

    try:
        import stubborn  # noqa: F401
    except ImportError as exc:
        checks.append(
            Check(
                id="core.import",
                status="fail",
                message=f"stubborn-stub not importable: {exc}",
                hint="pip install stubborn-stub",
            )
        )
        return checks

    checks.append(
        Check(
            id="core.import",
            status="pass",
            message="stubborn-stub importable",
        )
    )
    checks.append(
        Check(
            id="core.version",
            status="info",
            message=f"stubborn-stub {__version__}",
        )
    )

    if importlib.util.find_spec("google.protobuf") is None:
        checks.append(
            Check(
                id="core.scip_extra",
                status="warn",
                message="protobuf runtime not installed ([scip] extra missing)",
                hint=_SCIP_EXTRA_HINT,
            )
        )
    else:
        checks.append(
            Check(
                id="core.scip_extra",
                status="pass",
                message="protobuf runtime available for binary SCIP ingest",
            )
        )
    return checks


def signal_checks(root: Path) -> list[Check]:
    signals = discover_project_signals(root)
    checks: list[Check] = []
    if not signals:
        checks.append(
            Check(
                id="project.signals",
                status="info",
                message="no known build/index/config signals in project root",
            )
        )
        return checks

    by_kind = Counter(signal.kind for signal in signals)
    parts = [f"{kind}={count}" for kind, count in sorted(by_kind.items())]
    checks.append(
        Check(
            id="project.signals",
            status="info",
            message=f"detected signals: {', '.join(parts)}",
        )
    )
    for signal in signals:
        checks.append(
            Check(
                id=f"project.signal.{signal.kind}",
                status="info",
                message=signal.relative_path,
            )
        )

    if by_kind.get("scip", 0) and by_kind.get("openapi", 0):
        checks.append(
            Check(
                id="project.index_sources",
                status="info",
                message=(
                    "multiple index sources detected; stubborn does not auto-select SCIP vs OpenAPI"
                ),
                hint=(
                    "Code graph: stubborn index --scip <file> --out <db> (stubborn-stub). "
                    "Contract graph: stubborn index-openapi --openapi <file> "
                    "--service <name> --workspace <name> --out <db> (stubborn-stub; "
                    "service and workspace must be explicit per ADR-011)."
                ),
            )
        )
    return checks


def _discover_db(root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    for candidate in (root / "metadata" / "symbols.db", root / "symbols.db"):
        if candidate.is_file():
            return candidate
    return None


def database_checks(
    root: Path,
    *,
    db_path: Path | None,
    workspace: str | None,
) -> list[Check]:
    checks: list[Check] = []
    resolved = _discover_db(root, db_path)

    if resolved is None:
        checks.append(
            Check(
                id="db.present",
                status="warn",
                message="no symbols.db found (single-repo legacy mode needs no workspace)",
                hint=(
                    "Quick demo: stubborn try  "
                    "or: stubborn index --fixture minimal --out metadata/symbols.db "
                    "(stubborn-stub)"
                ),
            )
        )
        return checks

    if not resolved.is_file():
        checks.append(
            Check(
                id="db.present",
                status="fail",
                message=f"symbol graph not found: {resolved}",
                hint="Run: stubborn index --scip <fixture-or-index.scip> --out <db> (stubborn-stub)",
            )
        )
        return checks

    checks.append(
        Check(
            id="db.present",
            status="pass",
            message=f"symbol graph: {resolved}",
        )
    )

    try:
        conn = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
        try:
            schema_version = read_schema_version(conn)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        checks.append(
            Check(
                id="db.readable",
                status="fail",
                message=f"cannot read SQLite graph: {exc}",
            )
        )
        return checks

    checks.append(
        Check(
            id="db.schema",
            status="pass" if schema_version == 4 else "warn",
            message=f"schema version {schema_version}",
            hint=None if schema_version == 4 else "Re-index with the current stubborn-stub release",
        )
    )

    if workspace is not None:
        if schema_version is None or schema_version < 3:
            checks.append(
                Check(
                    id="db.workspace",
                    status="warn",
                    message=(
                        "workspace view requires schema v3+, found "
                        f"v{schema_version if schema_version is not None else 'unknown'}"
                    ),
                    hint="Re-index with the current stubborn-stub release",
                )
            )
        else:
            try:
                summaries = workspace_run_summaries(resolved, workspace=workspace)
            except ValueError as exc:
                checks.append(
                    Check(
                        id="db.workspace",
                        status="fail",
                        message=str(exc),
                    )
                )
                return checks
            repo_keys = sorted(item.repo_key for item in summaries)
            checks.append(
                Check(
                    id="db.workspace",
                    status="pass",
                    message=f"workspace {workspace!r}: {len(repo_keys)} repo(s)",
                )
            )
            for repo_key in repo_keys:
                item = next(s for s in summaries if s.repo_key == repo_key)
                checks.append(
                    Check(
                        id=f"db.workspace.repo.{repo_key}",
                        status="info",
                        message=(
                            f"kind={item.run_kind}, symbols={item.symbol_count}, "
                            f"edges={item.edge_count}, contract_bindings={item.contract_binding_count}"
                        ),
                    )
                )
    else:
        try:
            info = read_info(resolved, migrate=False)
        except ValueError as exc:
            checks.append(
                Check(
                    id="db.index_run",
                    status="warn",
                    message=str(exc),
                    hint="stubborn index --scip <source> --out <db> (stubborn-stub)",
                )
            )
            return checks
        checks.append(
            Check(
                id="db.index_run",
                status="pass",
                message=(
                    f"latest run {info.index_run_id}: symbols={info.symbol_count}, "
                    f"edges={info.edge_count}, mode={info.mode}, kind={info.run_kind}"
                ),
            )
        )
        if info.workspace:
            checks.append(
                Check(
                    id="db.workspace_name",
                    status="info",
                    message=f"workspace={info.workspace}, repo={info.repo_key or '(legacy)'}",
                )
            )

    if schema_version == 4:
        bindings = list_contract_bindings(resolved, workspace=workspace)
        if bindings:
            tiers = Counter(binding.evidence for binding in bindings)
            tier_text = ", ".join(f"{key}={value}" for key, value in sorted(tiers.items()))
            checks.append(
                Check(
                    id="db.contract_bindings",
                    status="info",
                    message=f"contract bindings: {len(bindings)} ({tier_text})",
                )
            )
    return checks


def delegation_hints(signals: list[ProjectSignal]) -> list[Check]:
    hints: list[Check] = []
    kinds = {signal.kind for signal in signals}
    if kinds & {"mcp_config"}:
        hints.append(
            Check(
                id="delegate.mcp",
                status="info",
                message="MCP setup is diagnosed by stubborn-mcp",
                hint="Run: stubborn-mcp doctor (stubborn-mcp package)",
            )
        )
    if kinds & {"build", "scip"} or not kinds:
        hints.append(
            Check(
                id="delegate.indexer",
                status="info",
                message="scip-java toolchain is not checked by stubborn-stub",
                hint=(
                    "Generate index.scip with scip-java, then stubborn index; future: "
                    "stubborn-indexer doctor (stubborn-indexer package)"
                ),
            )
        )
    return hints
