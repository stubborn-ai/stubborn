"""Tests for binary SCIP protobuf ingest."""

from __future__ import annotations

from pathlib import Path

import pytest

from scip_fixtures import build_minimal_index, write_streaming_scip
from stubborn.graph.prune import prune_context
from stubborn.ingest.scip import load_scip_index
from stubborn.ingest.stream import SCIP_MAGIC, parse_index_bytes
from stubborn.store.writer import IndexWriter

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "examples" / "fixtures"


@pytest.fixture(scope="module")
def minimal_scip_bytes() -> bytes:
    return write_streaming_scip(build_minimal_index())


def test_parse_streaming_and_monolithic(minimal_scip_bytes: bytes) -> None:
    streaming = parse_index_bytes(minimal_scip_bytes)
    assert streaming.metadata is not None
    assert len(streaming.documents) == 1

    monolithic = build_minimal_index().SerializeToString()
    parsed_mono = parse_index_bytes(monolithic)
    assert len(parsed_mono.documents) == 1
    assert parsed_mono.documents[0].language == "java"


def test_parse_with_optional_magic_prefix(minimal_scip_bytes: bytes) -> None:
    parsed = parse_index_bytes(SCIP_MAGIC + minimal_scip_bytes)
    assert parsed.metadata is not None


def test_language_inferred_from_path_when_field_missing(tmp_path: Path) -> None:
    index = build_minimal_index()
    index.documents[0].ClearField("language")

    scip_path = tmp_path / "index.scip"
    scip_path.write_bytes(write_streaming_scip(index))

    snapshot = load_scip_index(scip_path)
    assert snapshot.language == "java"


def test_load_binary_scip_roundtrip(tmp_path: Path, minimal_scip_bytes: bytes) -> None:
    scip_path = tmp_path / "index.scip"
    scip_path.write_bytes(minimal_scip_bytes)

    snapshot = load_scip_index(scip_path)
    assert len(snapshot.symbols) == 4
    assert snapshot.language == "java"
    assert any(edge.edge_kind == "type" for edge in snapshot.edges)
    assert any(edge.edge_kind == "reference" for edge in snapshot.edges)

    db = tmp_path / "symbols.db"
    IndexWriter(db).write(snapshot)

    target = "semanticdb maven com/example/OrderService#process()."
    graph = prune_context(db, target)
    stable_ids = {symbol.stable_id for symbol in graph.symbols}
    assert target in stable_ids
    assert "semanticdb maven com/example/Order#" in stable_ids


def test_examples_binary_fixture_matches_json() -> None:
    binary_path = FIXTURE_DIR / "minimal.scip"
    json_path = FIXTURE_DIR / "minimal.json"

    if not binary_path.exists():
        binary_path.write_bytes(write_streaming_scip(build_minimal_index()))

    binary_snapshot = load_scip_index(binary_path)
    json_snapshot = load_scip_index(json_path)

    assert {s.stable_id for s in binary_snapshot.symbols} == {
        s.stable_id for s in json_snapshot.symbols
    }
