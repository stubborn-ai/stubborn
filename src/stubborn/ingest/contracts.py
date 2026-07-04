"""Load explicit contract manifests into Stubborn contract snapshots."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stubborn.store.reader import resolve_stable_id
from stubborn.store.writer import (
    ContractBindingRecord,
    ContractEndpointRecord,
    ContractSchemaConstraintRecord,
    ContractSnapshot,
)

_PATH_PARAM_RE = re.compile(r"\{([^}/]+)\}")
_DEFAULT_SOURCE_PREFIX = "manual"


def load_contract_manifest(path: str | Path) -> dict[str, Any]:
    """Load a JSON-compatible contract manifest.

    The first public format intentionally stays small and explicit. It accepts
    JSON-compatible YAML files because JSON is a YAML subset, but does not parse
    arbitrary YAML syntax.
    """
    manifest_path = Path(path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def contract_snapshot_from_manifest(
    manifest_path: str | Path,
    *,
    db_path: str | Path | None = None,
    workspace: str | None = None,
    default_evidence: str = "declared",
    source: str | None = None,
    project_root: str | None = None,
) -> tuple[ContractSnapshot, str | None, str | None]:
    """Convert an explicit manifest into a ContractSnapshot plus scope metadata."""
    manifest_file = Path(manifest_path)
    manifest = load_contract_manifest(manifest_file)
    resolved_workspace = workspace or manifest.get("workspace")
    repo_key = manifest.get("contract_repo") or manifest.get("bridge_repo")
    source_label = source or f"{_DEFAULT_SOURCE_PREFIX}:{manifest_file.as_posix()}"

    endpoints = tuple(
        _endpoint_from_manifest(
            endpoint,
            db_path=db_path,
            workspace=resolved_workspace,
            default_evidence=default_evidence,
            source=source_label,
        )
        for endpoint in manifest.get("endpoints", [])
    )

    snapshot = ContractSnapshot(
        scip_source=manifest_file.as_posix(),
        project_root=project_root or manifest.get("project_root") or repo_key,
        language="openapi",
        endpoints=endpoints,
    )
    return snapshot, resolved_workspace, repo_key


def _endpoint_from_manifest(
    endpoint: dict[str, Any],
    *,
    db_path: str | Path | None,
    workspace: str | None,
    default_evidence: str,
    source: str,
) -> ContractEndpointRecord:
    method = endpoint["method"].upper()
    service = endpoint["service"]
    version = endpoint.get("version", "v1")
    address = endpoint["path"]
    bindings = [
        *_bindings_from_manifest(
            endpoint.get("providers", ()),
            role="provider",
            db_path=db_path,
            workspace=workspace,
            default_evidence=default_evidence,
            source=source,
        ),
        *_bindings_from_manifest(
            endpoint.get("consumers", ()),
            role="consumer",
            db_path=db_path,
            workspace=workspace,
            default_evidence=default_evidence,
            source=source,
        ),
        *_bindings_with_roles(
            endpoint.get("bindings", ()),
            db_path=db_path,
            workspace=workspace,
            default_evidence=default_evidence,
            source=source,
        ),
    ]

    return ContractEndpointRecord(
        stable_id=endpoint.get("stable_id") or f"openapi {service}:{version} {method} {address}",
        protocol=endpoint.get("protocol", "http"),
        service=service,
        version=version,
        method_or_verb=method,
        address=address,
        display_name=endpoint.get("display_name") or f"{method} {address}",
        schema_constraints=_constraints_from_endpoint(endpoint),
        bindings=tuple(bindings),
    )


def _bindings_from_manifest(
    entries: Any,
    *,
    role: str,
    db_path: str | Path | None,
    workspace: str | None,
    default_evidence: str,
    source: str,
) -> list[ContractBindingRecord]:
    return [
        _binding_from_manifest(
            entry,
            role=role,
            db_path=db_path,
            workspace=workspace,
            default_evidence=default_evidence,
            source=source,
        )
        for entry in entries
    ]


def _bindings_with_roles(
    entries: Any,
    *,
    db_path: str | Path | None,
    workspace: str | None,
    default_evidence: str,
    source: str,
) -> list[ContractBindingRecord]:
    return [
        _binding_from_manifest(
            entry,
            role=entry["role"],
            db_path=db_path,
            workspace=workspace,
            default_evidence=default_evidence,
            source=source,
        )
        for entry in entries
    ]


def _binding_from_manifest(
    entry: dict[str, Any],
    *,
    role: str,
    db_path: str | Path | None,
    workspace: str | None,
    default_evidence: str,
    source: str,
) -> ContractBindingRecord:
    code_stable_id = entry.get("code_stable_id")
    if code_stable_id is None:
        if db_path is None:
            raise ValueError("db_path is required when manifest bindings use repo/display_name")
        if workspace is None:
            raise ValueError("workspace is required when manifest bindings use repo/display_name")
        code_stable_id = resolve_stable_id(
            db_path,
            display_name=entry["display_name"],
            prefer_type=bool(entry.get("prefer_type", True)),
            workspace=workspace,
            repo_key=entry["repo"],
        )

    return ContractBindingRecord(
        code_stable_id=code_stable_id,
        role=role,
        evidence=entry.get("evidence", default_evidence),
        source=entry.get("source", source),
    )


def _constraints_from_endpoint(endpoint: dict[str, Any]) -> tuple[ContractSchemaConstraintRecord, ...]:
    explicit = [
        ContractSchemaConstraintRecord(
            location=item["location"],
            field_path=item["field_path"],
            type_name=item.get("type_name"),
            required=item.get("required"),
        )
        for item in endpoint.get("schema_constraints", ())
    ]
    if explicit:
        return tuple(explicit)

    return tuple(
        ContractSchemaConstraintRecord(
            location="path",
            field_path=match.group(1),
            required=True,
        )
        for match in _PATH_PARAM_RE.finditer(endpoint["path"])
    )
