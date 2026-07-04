"""Minimal OpenAPI 3.x adapter for Stubborn contract snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from stubborn.store.writer import (
    ContractEndpointRecord,
    ContractSchemaConstraintRecord,
    ContractSnapshot,
)

_HTTP_METHODS = frozenset({"get", "put", "post", "delete", "patch", "options", "head", "trace"})


def load_openapi_document(path: str | Path) -> dict[str, Any]:
    """Load an OpenAPI JSON/YAML document."""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        document = json.loads(text)
    else:
        document = yaml.safe_load(text)
    if not isinstance(document, dict):
        raise ValueError("OpenAPI document must be a mapping")
    return document


def openapi_snapshot_from_file(
    path: str | Path,
    *,
    service: str,
    version: str | None = None,
    project_root: str | None = None,
) -> ContractSnapshot:
    """Convert OpenAPI 3.x paths into contract endpoints without code bindings."""
    source = Path(path)
    document = load_openapi_document(source)
    openapi_version = str(document.get("openapi", ""))
    if not openapi_version.startswith("3."):
        raise ValueError("Only OpenAPI 3.x documents are supported")

    resolved_version = version or str(document.get("info", {}).get("version") or "v1")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("OpenAPI document must contain a paths object")

    endpoints: list[ContractEndpointRecord] = []
    for address, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        path_parameters = _parameter_constraints(path_item.get("parameters", ()))
        for method, operation in sorted(path_item.items()):
            method_lower = method.lower()
            if method_lower not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            method_upper = method_lower.upper()
            operation_parameters = _parameter_constraints(operation.get("parameters", ()))
            endpoints.append(
                ContractEndpointRecord(
                    stable_id=f"openapi {service}:{resolved_version} {method_upper} {address}",
                    protocol="http",
                    service=service,
                    version=resolved_version,
                    method_or_verb=method_upper,
                    address=address,
                    display_name=operation.get("operationId") or f"{method_upper} {address}",
                    schema_constraints=(
                        *path_parameters,
                        *operation_parameters,
                        *_request_body_constraints(operation.get("requestBody")),
                        *_response_body_constraints(operation.get("responses", {})),
                    ),
                    bindings=(),
                )
            )

    return ContractSnapshot(
        scip_source=source.as_posix(),
        project_root=project_root,
        language="openapi",
        endpoints=tuple(endpoints),
    )


def _parameter_constraints(parameters: Any) -> tuple[ContractSchemaConstraintRecord, ...]:
    constraints: list[ContractSchemaConstraintRecord] = []
    for parameter in parameters or ():
        if not isinstance(parameter, dict):
            continue
        location = parameter.get("in")
        if location not in {"path", "query", "header"}:
            continue
        name = parameter.get("name")
        if not name:
            continue
        constraints.append(
            ContractSchemaConstraintRecord(
                location=location,
                field_path=name,
                type_name=_schema_type_name(parameter.get("schema")),
                required=parameter.get("required"),
            )
        )
    return tuple(constraints)


def _request_body_constraints(request_body: Any) -> tuple[ContractSchemaConstraintRecord, ...]:
    if not isinstance(request_body, dict):
        return ()
    return tuple(
        ContractSchemaConstraintRecord(
            location="requestBody",
            field_path=media_type,
            type_name=_schema_type_name(media.get("schema")),
            required=request_body.get("required"),
        )
        for media_type, media in sorted((request_body.get("content") or {}).items())
        if isinstance(media, dict)
    )


def _response_body_constraints(responses: Any) -> tuple[ContractSchemaConstraintRecord, ...]:
    if not isinstance(responses, dict):
        return ()
    constraints: list[ContractSchemaConstraintRecord] = []
    for status, response in sorted(responses.items()):
        if not isinstance(response, dict):
            continue
        for media_type, media in sorted((response.get("content") or {}).items()):
            if not isinstance(media, dict):
                continue
            constraints.append(
                ContractSchemaConstraintRecord(
                    location="responseBody",
                    field_path=f"{status}.{media_type}",
                    type_name=_schema_type_name(media.get("schema")),
                    required=None,
                )
            )
    return tuple(constraints)


def _schema_type_name(schema: Any) -> str | None:
    if not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "type" in schema:
        schema_type = str(schema["type"])
        if schema_type == "array":
            item_type = _schema_type_name(schema.get("items"))
            return f"array[{item_type}]" if item_type else "array"
        return schema_type
    return None
