"""Helpers for building SCIP binary fixtures in tests."""

from __future__ import annotations

from stubborn.ingest.scip_proto import scip_pb2


def build_minimal_index() -> scip_pb2.Index:
    index = scip_pb2.Index()
    index.metadata.project_root = "file:///example"
    index.metadata.tool_info.name = "stubborn-test"
    index.metadata.tool_info.version = "0.2.0"

    document = index.documents.add()
    document.relative_path = "com/example/OrderService.java"
    document.language = "java"

    order_class = document.symbols.add()
    order_class.symbol = "semanticdb maven com/example/OrderService#"
    order_class.display_name = "OrderService"
    order_class.kind = scip_pb2.SymbolInformation.Class
    order_class.signature_documentation.text = "public class OrderService"

    process_method = document.symbols.add()
    process_method.symbol = "semanticdb maven com/example/OrderService#process()."
    process_method.display_name = "process"
    process_method.kind = scip_pb2.SymbolInformation.Method
    process_method.signature_documentation.text = "public void process(Order order)"

    order_type = document.symbols.add()
    order_type.symbol = "semanticdb maven com/example/Order#"
    order_type.display_name = "Order"
    order_type.kind = scip_pb2.SymbolInformation.Class
    order_type.signature_documentation.text = "public class Order"

    repo_method = document.symbols.add()
    repo_method.symbol = "semanticdb maven com/example/OrderRepository#findById()."
    repo_method.display_name = "findById"
    repo_method.kind = scip_pb2.SymbolInformation.Method
    repo_method.signature_documentation.text = "public Optional<Order> findById(String id)"

    rel_type = process_method.relationships.add()
    rel_type.symbol = order_type.symbol
    rel_type.is_type_definition = True

    rel_ref = order_class.relationships.add()
    rel_ref.symbol = repo_method.symbol
    rel_ref.is_reference = True

    def_occ = document.occurrences.add()
    def_occ.symbol = process_method.symbol
    def_occ.symbol_roles = int(scip_pb2.SymbolRole.Definition)

    use_occ = document.occurrences.add()
    use_occ.symbol = order_type.symbol
    use_occ.symbol_roles = int(scip_pb2.SymbolRole.ReadAccess)

    return index


def write_streaming_scip(index: scip_pb2.Index) -> bytes:
    """Write SCIP index in streaming field order (metadata, documents, …)."""
    chunks: list[bytes] = []

    if index.HasField("metadata"):
        chunks.append(_encode_field(1, index.metadata.SerializeToString()))

    for document in index.documents:
        chunks.append(_encode_field(2, document.SerializeToString()))

    for symbol in index.external_symbols:
        chunks.append(_encode_field(3, symbol.SerializeToString()))

    return b"".join(chunks)


def _encode_field(field_number: int, payload: bytes) -> bytes:
    tag = _encode_varint((field_number << 3) | 2)
    length = _encode_varint(len(payload))
    return tag + length + payload


def _encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        bits = value & 0x7F
        value >>= 7
        out.append(bits | (0x80 if value else 0))
        if not value:
            break
    return bytes(out)
