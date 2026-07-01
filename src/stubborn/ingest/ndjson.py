"""Parse newline-delimited JSON SCIP indexes (scip-java TYPED_NDJSON)."""

from __future__ import annotations

from google.protobuf import json_format

from stubborn.ingest.scip_proto import scip_pb2
from stubborn.ingest.stream import ParsedIndex


def parse_ndjson_index(data: bytes | str) -> ParsedIndex:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    parsed = ParsedIndex()

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        partial = scip_pb2.Index()
        try:
            json_format.Parse(stripped, partial)
        except json_format.ParseError as exc:
            raise ValueError(f"invalid SCIP ndjson at line {line_number}: {exc}") from exc

        if partial.HasField("metadata"):
            if parsed.metadata is not None:
                raise ValueError("metadata field must appear only once in ndjson stream")
            parsed.metadata = partial.metadata

        parsed.documents.extend(partial.documents)
        parsed.external_symbols.extend(partial.external_symbols)

    if not parsed.metadata and not parsed.documents and not parsed.external_symbols:
        raise ValueError("empty SCIP ndjson payload")
    return parsed
