"""Tests for contract graph traversal during pruning."""

from __future__ import annotations

from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.ingest.models import IndexSnapshot, SymbolRecord
from stubborn.store.writer import (
    ContractBindingRecord,
    ContractEndpointRecord,
    ContractSnapshot,
    IndexWriter,
)

PROVIDER = "semanticdb maven com/example/customers/OwnerResource#getOwner()."
CONSUMER = "semanticdb maven com/example/visits/CustomersClient#getOwner()."
ENDPOINT = "openapi customers-service:v1 GET /owners/{ownerId}"


def _write_code_repos(db: Path) -> IndexWriter:
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
    return writer


def _write_contract(
    writer: IndexWriter,
    *,
    provider_evidence: str = "strong",
    consumer_evidence: str = "declared",
) -> None:
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
                    bindings=(
                        ContractBindingRecord(
                            code_stable_id=PROVIDER,
                            role="provider",
                            evidence=provider_evidence,
                            source="openapi-generated-server",
                        ),
                        ContractBindingRecord(
                            code_stable_id=CONSUMER,
                            role="consumer",
                            evidence=consumer_evidence,
                            source="manual:contracts/http.yml",
                        ),
                    ),
                ),
            ),
        ),
        workspace="petclinic",
        repo_key="petclinic-contracts",
    )


def test_contract_prune_crosses_provider_to_consumer(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    writer = _write_code_repos(db)
    _write_contract(writer)

    graph = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10),
    )

    assert {symbol.stable_id for symbol in graph.symbols} == {PROVIDER, CONSUMER}
    assert graph.contract_edges
    assert any(
        edge.from_stable_id == PROVIDER
        and edge.to_stable_id == CONSUMER
        and edge.endpoint_stable_id == ENDPOINT
        and edge.evidence == "declared"
        for edge in graph.contract_edges
    )
    assert graph.edges == []


def test_contract_prune_crosses_consumer_to_provider(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    writer = _write_code_repos(db)
    _write_contract(writer)

    graph = prune_context(
        db,
        CONSUMER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10),
    )

    assert {symbol.stable_id for symbol in graph.symbols} == {PROVIDER, CONSUMER}
    assert any(
        edge.from_stable_id == CONSUMER
        and edge.to_stable_id == PROVIDER
        and edge.endpoint_stable_id == ENDPOINT
        for edge in graph.contract_edges
    )


def test_strict_prune_excludes_inferred_contract_bindings(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    writer = _write_code_repos(db)
    _write_contract(writer, consumer_evidence="inferred")

    smart = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10, prune_mode="smart"),
    )
    strict = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10, prune_mode="strict"),
    )

    assert CONSUMER in {symbol.stable_id for symbol in smart.symbols}
    assert any(edge.evidence == "inferred" for edge in smart.contract_edges)
    assert {symbol.stable_id for symbol in strict.symbols} == {PROVIDER}
    assert strict.contract_edges == []


def test_prune_without_contract_data_keeps_empty_contract_edges(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    _write_code_repos(db)

    graph = prune_context(
        db,
        PROVIDER,
        workspace="petclinic",
        budget=ContextBudget(call_closure_depth=1, max_symbols=10),
    )

    assert {symbol.stable_id for symbol in graph.symbols} == {PROVIDER}
    assert graph.edges == []
    assert graph.contract_edges == []
