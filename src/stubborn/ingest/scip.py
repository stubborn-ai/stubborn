"""Load SCIP index files into in-memory snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from stubborn.ingest.enrich import enrich_snapshot_edges
from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord

SCIP_MAGIC = b"\x00scip\x00"
_SCIP_EXTRA_MESSAGE = (
    "SCIP binary/NDJSON ingest requires the protobuf runtime. "
    "Install it with `pip install stubborn-stub[scip]`."
)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_scip_index(
    scip_path: str | Path,
    *,
    project_root: str | None = None,
) -> IndexSnapshot:
    """Load a SCIP index file.

    Supports:
    - Binary protobuf ``.scip`` (scip-java, scip-clang, …)
    - Newline-delimited JSON ``.scip.ndjson``
    - JSON fixtures ``.json`` for tests and examples
    """
    path = Path(scip_path)
    if not path.exists():
        raise FileNotFoundError(path)

    name = path.name.lower()
    if path.suffix.lower() == ".json":
        return _load_json_fixture(path, project_root=project_root)

    if name.endswith(".scip.ndjson"):
        parse_ndjson_index, parsed_index_to_snapshot = _load_ndjson_ingest()
        parsed = parse_ndjson_index(path.read_bytes())
        return parsed_index_to_snapshot(
            parsed,
            scip_source=str(path),
            scip_hash=_file_hash(path),
            project_root=project_root,
        )

    if path.suffix.lower() == ".scip" or name.endswith(".scip"):
        return _load_scip_protobuf(path, project_root=project_root)

    raise ValueError(
        f"Unsupported SCIP input: {path}. Use .scip, .scip.ndjson, or .json (fixture)."
    )


def _raise_scip_extra_import_error(exc: ModuleNotFoundError) -> None:
    name = exc.name or ""
    if name == "google" or name.startswith("google.protobuf"):
        raise ImportError(_SCIP_EXTRA_MESSAGE) from exc
    raise exc


def _load_ndjson_ingest():
    try:
        from stubborn.ingest.extract import parsed_index_to_snapshot
        from stubborn.ingest.ndjson import parse_ndjson_index
    except ModuleNotFoundError as exc:
        _raise_scip_extra_import_error(exc)
    return parse_ndjson_index, parsed_index_to_snapshot


def _load_binary_ingest():
    try:
        from stubborn.ingest.extract import parsed_index_to_snapshot
        from stubborn.ingest.stream import parse_index_bytes
    except ModuleNotFoundError as exc:
        _raise_scip_extra_import_error(exc)
    return parse_index_bytes, parsed_index_to_snapshot


def _load_json_fixture(path: Path, *, project_root: str | None) -> IndexSnapshot:
    """Load a minimal JSON fixture used by tests and examples."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "documents" in payload:
        symbols: list[SymbolRecord] = []
        edges: list[EdgeRecord] = []
        for document in payload["documents"]:
            rel_path = document.get("relative_path")
            for item in document.get("symbols", []):
                symbols.append(
                    SymbolRecord(
                        stable_id=item["stable_id"],
                        display_name=item.get("display_name"),
                        kind=item.get("kind"),
                        signature=item.get("signature"),
                        documentation=item.get("documentation"),
                        relative_path=item.get("relative_path", rel_path),
                    )
                )
            for item in document.get("edges", []):
                edges.append(
                    EdgeRecord(
                        from_stable_id=item["from"],
                        to_stable_id=item["to"],
                        edge_kind=item.get("edge_kind", "reference"),
                    )
                )
    else:
        symbols = [
            SymbolRecord(
                stable_id=item["stable_id"],
                display_name=item.get("display_name"),
                kind=item.get("kind"),
                signature=item.get("signature"),
                documentation=item.get("documentation"),
                relative_path=item.get("relative_path"),
            )
            for item in payload.get("symbols", [])
        ]
        edges = [
            EdgeRecord(
                from_stable_id=item["from"],
                to_stable_id=item["to"],
                edge_kind=item.get("edge_kind", "reference"),
            )
            for item in payload.get("edges", [])
        ]
    edges = enrich_snapshot_edges(symbols, edges)
    return IndexSnapshot(
        scip_source=str(path),
        symbols=symbols,
        edges=edges,
        project_root=project_root or payload.get("project_root"),
        scip_hash=_file_hash(path),
        language=payload.get("language"),
    )


def _load_scip_protobuf(path: Path, *, project_root: str | None) -> IndexSnapshot:
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Empty SCIP index file: {path}")

    parse_index_bytes, parsed_index_to_snapshot = _load_binary_ingest()
    parsed = parse_index_bytes(data)
    return parsed_index_to_snapshot(
        parsed,
        scip_source=str(path),
        scip_hash=_file_hash(path),
        project_root=project_root,
    )
