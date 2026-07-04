"""Direct tests for workspace-aware store helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from stubborn.ingest.models import IndexSnapshot, SymbolRecord
from stubborn.store.reader import latest_index_run_ids, workspace_run_summaries
from stubborn.store.writer import (
    ContractEndpointRecord,
    ContractSnapshot,
    IndexWriter,
    read_info,
    register_repo,
)


def test_register_repo_upserts_workspace_metadata(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"

    first_id = register_repo(
        db,
        repo_key="orders",
        workspace="acme",
        root="/workspace/orders",
        language="java",
    )
    second_id = register_repo(
        db,
        repo_key="orders",
        workspace="acme",
        root=None,
        language="kotlin",
    )

    conn = sqlite3.connect(db)
    try:
        workspace_row = conn.execute(
            "SELECT name FROM workspace WHERE name = 'acme'",
        ).fetchone()
        repo_row = conn.execute(
            """
            SELECT w.name, r.repo_key, r.root, r.language
            FROM repo r
            JOIN workspace w ON w.id = r.workspace_id
            WHERE r.repo_key = 'orders'
            """,
        ).fetchone()
    finally:
        conn.close()

    assert first_id == second_id
    assert workspace_row == ("acme",)
    assert repo_row == ("acme", "orders", "/workspace/orders", "kotlin")


def test_workspace_run_summaries_and_latest_run_ids(tmp_path: Path) -> None:
    db = tmp_path / "symbols.db"
    writer = IndexWriter(db)

    code_a_run = writer.write(
        IndexSnapshot(
            scip_source="repo-a.json",
            symbols=[
                SymbolRecord(
                    stable_id="semanticdb maven com/example/A#",
                    display_name="A",
                    kind="class",
                )
            ],
        ),
        workspace="acme",
        repo_key="repo-a",
    )
    code_b_run = writer.write(
        IndexSnapshot(
            scip_source="repo-b.json",
            symbols=[
                SymbolRecord(
                    stable_id="semanticdb maven com/example/B#",
                    display_name="B",
                    kind="class",
                )
            ],
        ),
        workspace="acme",
        repo_key="repo-b",
    )
    contract_run = writer.write_contract(
        ContractSnapshot(
            scip_source="contracts.json",
            endpoints=(
                ContractEndpointRecord(
                    stable_id="openapi service:v1 GET /ping",
                    protocol="http",
                    address="/ping",
                ),
            ),
        ),
        workspace="acme",
        repo_key="repo-b",
    )

    summaries = workspace_run_summaries(db, workspace="acme")
    summary_pairs = {(item.repo_key, item.run_kind) for item in summaries}

    conn = sqlite3.connect(db)
    try:
        repo_b_code_ids = latest_index_run_ids(
            conn,
            workspace="acme",
            repo_key="repo-b",
            run_kind="code",
        )
        repo_b_contract_ids = latest_index_run_ids(
            conn,
            workspace="acme",
            repo_key="repo-b",
            run_kind="contract",
        )
    finally:
        conn.close()

    assert summary_pairs == {
        ("repo-a", "code"),
        ("repo-b", "code"),
        ("repo-b", "contract"),
    }
    assert {item.index_run_id for item in summaries} == {
        code_a_run,
        code_b_run,
        contract_run,
    }
    assert repo_b_code_ids == [code_b_run]
    assert repo_b_contract_ids == [contract_run]
    assert read_info(db, index_run_id=contract_run).run_kind == "contract"
