"""Streaming SCIP index parser (scip-java / scip-code compatible)."""

from __future__ import annotations

from dataclasses import dataclass, field

from stubborn.ingest.scip_proto import scip_pb2

SCIP_MAGIC = b"\x00scip\x00"

_METADATA_FIELD = 1
_DOCUMENTS_FIELD = 2
_EXTERNAL_SYMBOLS_FIELD = 3


@dataclass
class ParsedIndex:
    metadata: scip_pb2.Metadata | None = None
    documents: list[scip_pb2.Document] = field(default_factory=list)
    external_symbols: list[scip_pb2.SymbolInformation] = field(default_factory=list)


def strip_optional_magic(data: bytes) -> bytes:
    if data.startswith(SCIP_MAGIC):
        return data[len(SCIP_MAGIC) :]
    return data


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte <= 0x7F:
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint exceeds 64 bits")
    raise ValueError("unexpected end of data while reading varint")


def parse_index_bytes(data: bytes) -> ParsedIndex:
    """Parse a SCIP index payload field-by-field.

    Compatible with scip-java ``index.scip`` output and monolithic ``Index`` messages.
    """
    payload = strip_optional_magic(data)
    if not payload:
        return ParsedIndex()

    try:
        return _parse_streaming(payload)
    except ValueError:
        return _parse_monolithic(payload)


def _parse_streaming(payload: bytes) -> ParsedIndex:
    parsed = ParsedIndex()
    pos = 0
    length = len(payload)

    while pos < length:
        tag, pos = _read_varint(payload, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7
        if wire_type != 2:
            raise ValueError(f"unsupported wire type {wire_type} for field {field_number}")

        chunk_len, pos = _read_varint(payload, pos)
        chunk = payload[pos : pos + chunk_len]
        pos += chunk_len

        if field_number == _METADATA_FIELD:
            if parsed.metadata is not None:
                raise ValueError("metadata field must appear only once")
            message = scip_pb2.Metadata()
            message.ParseFromString(chunk)
            parsed.metadata = message
        elif field_number == _DOCUMENTS_FIELD:
            message = scip_pb2.Document()
            message.ParseFromString(chunk)
            parsed.documents.append(message)
        elif field_number == _EXTERNAL_SYMBOLS_FIELD:
            message = scip_pb2.SymbolInformation()
            message.ParseFromString(chunk)
            parsed.external_symbols.append(message)
        else:
            continue

    if not parsed.metadata and not parsed.documents and not parsed.external_symbols:
        raise ValueError("empty SCIP index payload")
    return parsed


def _parse_monolithic(payload: bytes) -> ParsedIndex:
    index = scip_pb2.Index()
    index.ParseFromString(payload)
    parsed = ParsedIndex(
        metadata=index.metadata if index.HasField("metadata") else None,
        documents=list(index.documents),
        external_symbols=list(index.external_symbols),
    )
    if not parsed.metadata and not parsed.documents and not parsed.external_symbols:
        raise ValueError("empty SCIP index payload")
    return parsed
