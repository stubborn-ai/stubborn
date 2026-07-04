"""Optional dependency boundary tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "examples" / "fixtures"


class _BlockProtobufImport:
    def find_spec(self, fullname: str, path=None, target=None):
        if fullname == "google.protobuf" or fullname.startswith("google.protobuf."):
            raise ModuleNotFoundError(
                "No module named 'google.protobuf'",
                name=fullname,
            )
        return None


def _unload_protobuf_bound_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    prefixes = (
        "google.protobuf",
        "stubborn.api",
        "stubborn.cli",
        "stubborn.ingest.extract",
        "stubborn.ingest.ndjson",
        "stubborn.ingest.scip",
        "stubborn.ingest.scip_proto",
        "stubborn.ingest.stream",
    )
    for name in list(sys.modules):
        if name in prefixes or any(name.startswith(f"{prefix}.") for prefix in prefixes):
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_core_api_cli_and_json_fixture_do_not_require_protobuf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _unload_protobuf_bound_modules(monkeypatch)
    monkeypatch.setattr(sys, "meta_path", [_BlockProtobufImport(), *sys.meta_path])

    importlib.import_module("stubborn.api")
    importlib.import_module("stubborn.cli")
    scip = importlib.import_module("stubborn.ingest.scip")

    snapshot = scip.load_scip_index(FIXTURES / "minimal.json")

    assert snapshot.symbols
    assert snapshot.edges


def test_binary_scip_ingest_reports_missing_scip_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _unload_protobuf_bound_modules(monkeypatch)
    monkeypatch.setattr(sys, "meta_path", [_BlockProtobufImport(), *sys.meta_path])
    scip = importlib.import_module("stubborn.ingest.scip")

    with pytest.raises(ImportError, match=r"stubborn-stub\[scip\]"):
        scip.load_scip_index(FIXTURES / "minimal.scip")
