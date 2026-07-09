"""Run stubborn-stub doctor checks."""

from __future__ import annotations

from pathlib import Path

from stubborn import __version__
from stubborn.doctor.checks import (
    database_checks,
    delegation_hints,
    runtime_checks,
    signal_checks,
)
from stubborn.doctor.models import DoctorReport
from stubborn.doctor.signals import discover_project_signals


def run_doctor(
    project_root: Path,
    *,
    db_path: Path | None = None,
    workspace: str | None = None,
    fix_hint: bool = True,
) -> DoctorReport:
    root = project_root.resolve()
    report = DoctorReport(
        version=__version__,
        cwd=str(root),
    )
    report.checks.extend(runtime_checks())
    signals = discover_project_signals(root)
    report.checks.extend(signal_checks(root))
    report.checks.extend(
        database_checks(root, db_path=db_path, workspace=workspace),
    )
    if fix_hint:
        report.checks.extend(delegation_hints(signals))
    return report
