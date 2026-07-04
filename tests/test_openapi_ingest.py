"""Tests for minimal OpenAPI contract ingest."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from typer.testing import CliRunner

from stubborn.api import get_context, index_openapi_contract
from stubborn.cli import app
from stubborn.ingest.models import IndexSnapshot, SymbolRecord
from stubborn.ingest.openapi import openapi_snapshot_from_file
from stubborn.store.writer import IndexWriter, read_info

SERVICE = "customers-service"
ENDPOINT = "openapi customers-service:v1 GET /owners/{ownerId}"
OWNER_RESOURCE = "semanticdb maven com/example/customers/OwnerResource#"


def _write_openapi(tmp_path: Path) -> Path:
    path = tmp_path / "openapi.yml"
    path.write_text(
        """
openapi: 3.0.3
info:
  title: Customers API
  version: v1
paths:
  /owners/{ownerId}:
    parameters:
      - name: ownerId
        in: path
        required: true
        schema:
          type: integer
    get:
      operationId: getOwner
      parameters:
        - name: includePets
          in: query
          required: false
          schema:
            type: boolean
      responses:
        "200":
          description: Owner found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Owner"
  /owners:
    post:
      operationId: createOwner
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/OwnerInput"
      responses:
        "201":
          description: Owner created
components:
  schemas:
    Owner:
      type: object
    OwnerInput:
      type: object
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_openapi_json(tmp_path: Path) -> Path:
    path = tmp_path / "openapi.json"
    path.write_text(
        """
{
  "openapi": "3.0.3",
  "info": {
    "title": "Customers API",
    "version": "v1"
  },
  "paths": {
    "/owners/{ownerId}": {
      "get": {
        "operationId": "getOwner",
        "parameters": [
          {
            "name": "ownerId",
            "in": "path",
            "required": true,
            "schema": {
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Owner found"
          }
        }
      }
    }
  }
}
""".lstrip(),
        encoding="utf-8",
    )
    return path


def _write_code_symbol(db: Path) -> None:
    IndexWriter(db).write(
        IndexSnapshot(
            scip_source="customers.json",
            language="java",
            symbols=[
                SymbolRecord(
                    stable_id=OWNER_RESOURCE,
                    display_name="OwnerResource",
                    kind="class",
                    signature="public class OwnerResource",
                    relative_path="src/OwnerResource.java",
                )
            ],
        ),
        workspace="petclinic",
        repo_key="customers-service",
    )


def test_openapi_loader_emits_endpoints_and_constraints(tmp_path: Path) -> None:
    snapshot = openapi_snapshot_from_file(
        _write_openapi(tmp_path),
        service=SERVICE,
        version="v1",
    )

    assert len(snapshot.endpoints) == 2
    owner = next(endpoint for endpoint in snapshot.endpoints if endpoint.stable_id == ENDPOINT)
    assert owner.protocol == "http"
    assert owner.display_name == "getOwner"
    assert owner.bindings == ()

    constraints = {(item.location, item.field_path, item.type_name, item.required) for item in owner.schema_constraints}
    assert ("path", "ownerId", "integer", True) in constraints
    assert ("query", "includePets", "boolean", False) in constraints
    assert ("responseBody", "200.application/json", "Owner", None) in constraints


def test_openapi_json_loader_does_not_require_yaml(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class BlockYamlImport:
        def find_spec(self, fullname: str, path=None, target=None):
            if fullname == "yaml":
                raise ImportError("blocked yaml import")
            return None

    monkeypatch.delitem(sys.modules, "yaml", raising=False)
    monkeypatch.setattr(sys, "meta_path", [BlockYamlImport(), *sys.meta_path])

    snapshot = openapi_snapshot_from_file(
        _write_openapi_json(tmp_path),
        service=SERVICE,
        version="v1",
    )

    assert len(snapshot.endpoints) == 1
    assert snapshot.endpoints[0].stable_id == ENDPOINT


def test_api_indexes_openapi_without_code_bindings(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_code_symbol(db)
    result = index_openapi_contract(
        _write_openapi(tmp_path),
        db_path=db,
        service=SERVICE,
        workspace="petclinic",
    )
    info = read_info(db, index_run_id=result.index_run_id)
    context = get_context(
        OWNER_RESOURCE,
        db_path=db,
        workspace="petclinic",
        format="stubborn-dsl",
        call_depth=1,
    )

    assert result.endpoint_count == 2
    assert result.binding_count == 0
    assert result.repo_key == "customers-service-openapi"
    assert info.run_kind == "contract"
    assert context.contract_edges == []
    assert "contracts:" not in context.text

    conn = sqlite3.connect(db)
    try:
        endpoint_count = conn.execute("SELECT COUNT(*) FROM contract_endpoint").fetchone()[0]
        binding_count = conn.execute("SELECT COUNT(*) FROM contract_binding").fetchone()[0]
    finally:
        conn.close()

    assert endpoint_count == 2
    assert binding_count == 0


def test_cli_index_openapi(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    openapi = _write_openapi(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "index-openapi",
            "--openapi",
            str(openapi),
            "--out",
            str(db),
            "--service",
            SERVICE,
            "--workspace",
            "petclinic",
        ],
    )

    assert result.exit_code == 0, result.stdout + result.stderr
    assert "OpenAPI endpoint(s)" in result.stdout
    assert "binding(s)" in result.stdout
    assert "run_kind=contract" in result.stdout
