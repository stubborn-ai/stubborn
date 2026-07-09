"""Passive project signal discovery for doctor (read-only, no inference)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BUILD_SIGNALS = (
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
)

SCIP_SIGNALS = (
    "index.scip",
)

OPENAPI_RELATIVE = (
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
    "src/main/resources/openapi.yaml",
    "src/main/resources/openapi.yml",
    "src/main/resources/openapi.json",
)

CONTRACT_SIGNALS = (
    "contracts/http.yml",
    "contracts/http.yaml",
)

OTHER_SIGNALS = (
    "metadata/symbols.db",
    "symbols.db",
    ".cursor/mcp.json",
)


@dataclass(frozen=True)
class ProjectSignal:
    kind: str
    relative_path: str


def discover_project_signals(root: Path) -> list[ProjectSignal]:
    """List known signal files that exist under ``root`` (no subprocess, no inference)."""
    root = root.resolve()
    found: list[ProjectSignal] = []

    for name in BUILD_SIGNALS:
        path = root / name
        if path.is_file():
            found.append(ProjectSignal(kind="build", relative_path=name))

    for name in SCIP_SIGNALS:
        path = root / name
        if path.is_file():
            found.append(ProjectSignal(kind="scip", relative_path=name))

    for name in OPENAPI_RELATIVE:
        path = root / name
        if path.is_file():
            found.append(ProjectSignal(kind="openapi", relative_path=name))

    for name in CONTRACT_SIGNALS:
        path = root / name
        if path.is_file():
            found.append(ProjectSignal(kind="contract_manifest", relative_path=name))

    for name in OTHER_SIGNALS:
        path = root / name
        if path.is_file():
            kind = "mcp_config" if name.endswith("mcp.json") else "symbols_db"
            found.append(ProjectSignal(kind=kind, relative_path=name))

    return found
