"""Data models for federated doctor reports (ADR-015 / ADR-016)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DOCTOR_REPORT_SCHEMA = "stubborn.doctor-report/v1"
PACKAGE_ID = "stubborn-stub"
DOCTOR_COMMAND = "stubborn doctor"

CheckStatus = Literal["pass", "warn", "fail", "skip", "info"]


@dataclass(frozen=True)
class Check:
    id: str
    status: CheckStatus
    message: str
    hint: str | None = None


@dataclass
class DoctorReport:
    package: str = PACKAGE_ID
    command: str = DOCTOR_COMMAND
    version: str = ""
    cwd: str = ""
    checks: list[Check] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema": DOCTOR_REPORT_SCHEMA,
            "package": self.package,
            "command": self.command,
            "version": self.version,
            "cwd": self.cwd,
            "exit": self.exit_code(),
            "checks": [
                {
                    "id": item.id,
                    "status": item.status,
                    "message": item.message,
                    "hint": item.hint,
                }
                for item in self.checks
            ],
        }

    def exit_code(self) -> int:
        if any(item.status == "fail" for item in self.checks):
            return 1
        if any(item.status == "warn" for item in self.checks):
            return 2
        return 0
