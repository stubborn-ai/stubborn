"""Convert parsed SCIP protobuf into Stubborn snapshot models."""

from __future__ import annotations

from stubborn.ingest.enrich import enrich_snapshot_edges
from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord
from stubborn.ingest.scip_proto import scip_pb2
from stubborn.ingest.stream import ParsedIndex

_DEFINITION_ROLE = int(scip_pb2.SymbolRole.Definition)


def parsed_index_to_snapshot(
    parsed: ParsedIndex,
    *,
    scip_source: str,
    scip_hash: str | None,
    project_root: str | None = None,
) -> IndexSnapshot:
    symbols: dict[str, SymbolRecord] = {}
    edges: list[EdgeRecord] = []

    for document in parsed.documents:
        rel_path = document.relative_path or None
        for symbol_info in document.symbols:
            _upsert_symbol(symbols, symbol_info, relative_path=rel_path)
            edges.extend(_edges_from_relationships(symbol_info))

        edges.extend(_edges_from_occurrences(document))

    for symbol_info in parsed.external_symbols:
        _upsert_symbol(symbols, symbol_info)
        edges.extend(_edges_from_relationships(symbol_info))

    edges = enrich_snapshot_edges(symbols, edges)

    language = _detect_language(parsed)
    resolved_root = project_root or (parsed.metadata.project_root if parsed.metadata else None)

    return IndexSnapshot(
        scip_source=scip_source,
        symbols=sorted(symbols.values(), key=lambda s: s.stable_id),
        edges=edges,
        project_root=resolved_root or None,
        scip_hash=scip_hash,
        language=language,
    )


def _detect_language(parsed: ParsedIndex) -> str | None:
    from collections import Counter

    languages = [
        document.language.strip().lower()
        for document in parsed.documents
        if document.language and document.language.strip()
    ]
    if languages:
        return Counter(languages).most_common(1)[0][0]

    for document in parsed.documents:
        path = (document.relative_path or "").lower()
        if path.endswith(".java"):
            return "java"
        if path.endswith((".kt", ".kts")):
            return "kotlin"
        if path.endswith((".scala", ".sc")):
            return "scala"
        if path.endswith((".cs",)):
            return "csharp"
        if path.endswith((".ts", ".tsx")):
            return "typescript"
        if path.endswith((".py",)):
            return "python"
        if path.endswith((".go",)):
            return "go"
        if path.endswith((".rs",)):
            return "rust"
    return None


def _kind_name(kind: int) -> str | None:
    if kind == scip_pb2.SymbolInformation.UnspecifiedKind:
        return None
    name = scip_pb2.SymbolInformation.Kind.Name(kind)
    if name == "UnspecifiedKind":
        return None
    return name.lower()


def _signature_text(symbol_info: scip_pb2.SymbolInformation) -> str | None:
    if symbol_info.HasField("signature_documentation"):
        text = symbol_info.signature_documentation.text.strip()
        if text:
            return text
    for line in symbol_info.documentation:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if stripped:
            return stripped
    return None


def _documentation_text(symbol_info: scip_pb2.SymbolInformation) -> str | None:
    prose = [
        line.strip()
        for line in symbol_info.documentation
        if line.strip() and not line.strip().startswith("```")
    ]
    if not prose:
        return None
    return "\n".join(prose)


def _upsert_symbol(
    store: dict[str, SymbolRecord],
    symbol_info: scip_pb2.SymbolInformation,
    *,
    relative_path: str | None = None,
) -> None:
    if not symbol_info.symbol:
        return
    store[symbol_info.symbol] = SymbolRecord(
        stable_id=symbol_info.symbol,
        display_name=symbol_info.display_name or None,
        kind=_kind_name(symbol_info.kind),
        signature=_signature_text(symbol_info),
        documentation=_documentation_text(symbol_info),
        relative_path=relative_path,
    )


def _edges_from_relationships(symbol_info: scip_pb2.SymbolInformation) -> list[EdgeRecord]:
    if not symbol_info.symbol:
        return []

    edges: list[EdgeRecord] = []
    for relationship in symbol_info.relationships:
        if not relationship.symbol:
            continue
        if relationship.is_type_definition:
            edges.append(EdgeRecord(symbol_info.symbol, relationship.symbol, "type"))
        if relationship.is_implementation:
            edges.append(EdgeRecord(symbol_info.symbol, relationship.symbol, "implementation"))
        if relationship.is_reference:
            edges.append(EdgeRecord(symbol_info.symbol, relationship.symbol, "reference"))
        if relationship.is_definition:
            edges.append(EdgeRecord(symbol_info.symbol, relationship.symbol, "definition"))
    return edges


def _occurrence_sort_key(occurrence: scip_pb2.Occurrence) -> tuple[int, int]:
    if occurrence.HasField("single_line_range"):
        row = occurrence.single_line_range
        return row.line, row.start_character
    if occurrence.HasField("multi_line_range"):
        row = occurrence.multi_line_range
        return row.start_line, row.start_character
    if len(occurrence.range) >= 2:
        return occurrence.range[0], occurrence.range[1]
    return 0, 0


def _edges_from_occurrences(document: scip_pb2.Document) -> list[EdgeRecord]:
    edges: list[EdgeRecord] = []
    enclosing_stack: list[str] = []

    for occurrence in sorted(document.occurrences, key=_occurrence_sort_key):
        if not occurrence.symbol:
            continue

        is_definition = (occurrence.symbol_roles & _DEFINITION_ROLE) != 0
        if is_definition:
            enclosing_stack.append(occurrence.symbol)
            continue

        if not enclosing_stack:
            continue

        enclosing = _resolve_enclosing_symbol(enclosing_stack)
        if enclosing is None:
            continue

        edges.append(EdgeRecord(enclosing, occurrence.symbol, "reference"))

    return edges


def _is_scip_local_symbol(symbol: str) -> bool:
    return symbol.startswith("local ") or symbol.startswith("local/")


def _resolve_enclosing_symbol(enclosing_stack: list[str]) -> str | None:
    for symbol in reversed(enclosing_stack):
        if not _is_scip_local_symbol(symbol):
            return symbol
    return None
