"""Tests for public contract ingest entrypoints."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from stubborn.api import get_context, index_contract_manifest
from stubborn.cli import app
from stubborn.ingest.models import IndexSnapshot, SymbolRecord
from stubborn.store.reader import list_contract_bindings
from stubborn.store.writer import IndexWriter, read_info

PROVIDER = "semanticdb maven com/example/customers/OwnerResource#getOwner()."
CONSUMER = "semanticdb maven com/example/visits/CustomersClient#getOwner()."
ENDPOINT = "openapi customers-service:v1 GET /owners/{ownerId}"


def _write_code_repos(db: Path) -> None:
    writer = IndexWriter(db)
    writer.write(
        IndexSnapshot(
            scip_source="customers.json",
            language="java",
            symbols=[
                SymbolRecord(
                    stable_id=PROVIDER,
                    display_name="OwnerResource",
                    kind="class",
                    signature="public class OwnerResource",
                    relative_path="src/OwnerResource.java",
                ),
            ],
        ),
        workspace="petclinic",
        repo_key="customers-service",
    )
    writer.write(
        IndexSnapshot(
            scip_source="visits.json",
            language="java",
            symbols=[
                SymbolRecord(
                    stable_id=CONSUMER,
                    display_name="CustomersClient",
                    kind="class",
                    signature="public interface CustomersClient",
                    relative_path="src/CustomersClient.java",
                ),
            ],
        ),
        workspace="petclinic",
        repo_key="visits-service",
    )


def _write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "contracts.json"
    manifest.write_text(
        json.dumps(
            {
                "workspace": "petclinic",
                "contract_repo": "petclinic-contracts",
                "endpoints": [
                    {
                        "service": "customers-service",
                        "version": "v1",
                        "method": "GET",
                        "path": "/owners/{ownerId}",
                        "providers": [
                            {
                                "repo": "customers-service",
                                "display_name": "OwnerResource",
                            },
                        ],
                        "consumers": [
                            {
                                "repo": "visits-service",
                                "display_name": "CustomersClient",
                            },
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_api_indexes_contract_manifest_and_context_uses_it(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_code_repos(db)
    manifest = _write_manifest(tmp_path)

    result = index_contract_manifest(manifest, db_path=db)
    info = read_info(db, index_run_id=result.index_run_id)
    bindings = list_contract_bindings(db, workspace="petclinic")
    context = get_context(
        PROVIDER,
        db_path=db,
        workspace="petclinic",
        format="stubborn-dsl",
        call_depth=1,
    )

    assert result.endpoint_count == 1
    assert result.binding_count == 2
    assert info.run_kind == "contract"
    assert {binding.evidence for binding in bindings} == {"declared"}
    assert {binding.endpoint_stable_id for binding in bindings} == {ENDPOINT}
    assert "contracts:" in context.text
    assert ENDPOINT in context.text
    assert context.contract_evidence_summary == {"declared": 2}


def test_cli_index_contract_manifest(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_code_repos(db)
    manifest = _write_manifest(tmp_path)
    runner = CliRunner()

    indexed = runner.invoke(
        app,
        ["index-contract", "--manifest", str(manifest), "--out", str(db)],
    )
    assert indexed.exit_code == 0, indexed.stdout + indexed.stderr
    assert "contract endpoint(s)" in indexed.stdout
    assert "run_kind=contract" in indexed.stdout

    context = runner.invoke(
        app,
        [
            "context",
            str(db),
            "--workspace",
            "petclinic",
            "--target",
            PROVIDER,
            "--format",
            "stubborn-dsl",
            "--call-depth",
            "1",
        ],
    )
    assert context.exit_code == 0, context.stdout + context.stderr
    assert "contracts:" in context.stdout
    assert ENDPOINT in context.stdout
