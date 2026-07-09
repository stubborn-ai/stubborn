"""Format doctor reports for humans and JSON consumers."""

from __future__ import annotations

import json

from stubborn.doctor.models import DoctorReport


def format_text(report: DoctorReport, *, fix_hint: bool = True) -> str:
    lines = [
        f"stubborn doctor — {report.cwd}",
        "",
    ]
    current_section: str | None = None
    for check in report.checks:
        section = check.id.split(".", 1)[0]
        if section != current_section:
            if current_section is not None:
                lines.append("")
            lines.append(section.capitalize())
            current_section = section
        prefix = _status_prefix(check.status)
        lines.append(f"  {prefix} {check.message}")
        if fix_hint and check.hint:
            lines.append(f"      → {check.hint}")

    lines.extend(["", f"Exit {report.exit_code()}"])
    return "\n".join(lines)


def format_json(report: DoctorReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


def _status_prefix(status: str) -> str:
    return {
        "pass": "✓",
        "warn": "⚠",
        "fail": "✗",
        "skip": "·",
        "info": "·",
    }.get(status, "·")
