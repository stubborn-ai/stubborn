"""Tests for contract evidence rendering and API exposure."""

from __future__ import annotations

from pathlib import Path

from stubborn.api import get_context
from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.models import IndexSnapshot, SymbolRecord
from stubborn.store.writer import (
    ContractBindingRecord,
    ContractEndpointRecord,
    ContractSchemaConstraintRecord,
    ContractSnapshot,
    IndexWriter,
)
from stubborn.weave.java_stub import weave_java_stub
from stubborn.weave.stubborn_dsl import weave_stubborn_dsl

PROVIDER = "semanticdb maven com/example/customers/OwnerResource#getOwner()."
CONSUMER = "semanticdb maven com/example/visits/CustomersClient#getOwner()."
ENDPOINT = "openapi customers-service:v1 GET /owners/{ownerId}"


def _write_contract_context(db: Path) -> None:
    writer = IndexWriter(db)
    writer.write(
        IndexSnapshot(
            scip_source="customers.json",
            language="java",
            symbols=[
                SymbolRecord(
                    stable_id=PROVIDER,
                    display_name="getOwner",
                    kind="method",
                    signature="Owner getOwner(Integer ownerId)",
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
                    display_name="getOwner",
                    kind="method",
                    signature="OwnerDto getOwner(Integer ownerId)",
                    relative_path="src/CustomersClient.java",
                ),
            ],
        ),
        workspace="petclinic",
        repo_key="visits-service",
    )
    writer.write_contract(
        ContractSnapshot(
            scip_source="contracts/openapi.json",
            language="openapi",
            endpoints=(
                ContractEndpointRecord(
                    stable_id=ENDPOINT,
                    protocol="http",
                    service="customers-service",
                    version="v1",
                    method_or_verb="GET",
                    address="/owners/{ownerId}",
                    display_name="GET /owners/{ownerId}",
                    schema_constraints=(
                        ContractSchemaConstraintRecord(
                            location="path",
                            field_path="ownerId",
                            type_name="integer",
                            required=True,
                        ),
                    ),
                    bindings=(
                        ContractBindingRecord(
                            code_stable_id=PROVIDER,
                            role="provider",
                            evidence="strong",
                            source="openapi-generated-server",
                        ),
                        ContractBindingRecord(
                            code_stable_id=CONSUMER,
                            role="consumer",
                            evidence="declared",
                            source="manual:contracts/http.yml",
                        ),
                    ),
                ),
            ),
        ),
        workspace="petclinic",
        repo_key="petclinic-contracts",
    )


def test_stubborn_dsl_renders_contracts_block(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_contract_context(db)

    graph = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10),
    )
    text = weave_stubborn_dsl(graph).text

    assert "contracts:" in text
    assert f"  http {ENDPOINT}" in text
    assert "provider OwnerResource.getOwner -> consumer CustomersClient.getOwner" in text
    assert "evidence=declared" in text
    assert "schema path.ownerId integer required" in text


def test_java_stub_does_not_render_contracts(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_contract_context(db)

    graph = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10),
    )
    text = weave_java_stub(graph).text

    assert "contracts:" not in text
    assert ENDPOINT not in text
    assert "evidence=" not in text


def test_api_exposes_contract_evidence_structured(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_contract_context(db)

    result = get_context(
        PROVIDER,
        db_path=db,
        workspace="petclinic",
        format="stubborn-dsl",
        call_depth=1,
    )

    assert result.contract_edges
    assert result.contract_evidence_summary == {"declared": 2}
    assert any(
        edge["endpoint_stable_id"] == ENDPOINT
        and edge["from_role"] == "provider"
        and edge["to_role"] == "consumer"
        and edge["evidence"] == "declared"
        for edge in result.contract_edges
    )
    assert any(
        endpoint["stable_id"] == ENDPOINT
        and endpoint["schema_constraints"][0]["field_path"] == "ownerId"
        for endpoint in result.contract_endpoints
    )
