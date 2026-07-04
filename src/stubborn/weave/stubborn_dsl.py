"""Emit Stubborn-DSL v1 text from a pruned symbol graph."""

from __future__ import annotations

import re

from stubborn.graph.prune import (
    ContractPrunedEdge,
    PrunedContractSchemaConstraint,
    PrunedGraph,
    PrunedSymbol,
)
from stubborn.tokens import estimate_tokens
from stubborn.weave._shared import (
    is_annotation_only,
    kind_bucket,
    select_type_symbols,
    short_name,
    short_target_name,
    sort_key,
    trim_for_token_budget,
)
from stubborn.weave.members import (
    format_stubborn_dsl_doc_lines,
    method_members_for_type,
    normalize_method_signature,
    resolve_target_type_id,
    type_includes_method_signatures,
)
from stubborn.weave.options import DEFAULT_WEAVE_OPTIONS, WeaveOptions
from stubborn.weave.stubborn_dsl_llm import LLM_GUIDE_LINES
from stubborn.weave.types import WeaveResult

_STUBBORN_DSL_VERSION = "1.0"
_ANNOTATION_RE = re.compile(r"@[\w.]+(?:\([^)]*\))?")
_TYPE_DECL_RE = re.compile(r"\b(class|interface|enum|record)\s+(\w+)")
_METHOD_KINDS = frozenset({"method", "constructor", "abstractmethod", "staticmethod"})
_KIND_CODES = {
    "class": "c",
    "interface": "i",
    "enum": "e",
    "record": "r",
}
_EDGE_ABBREV = {
    "reference": "ref",
    "type": "type",
    "implementation": "impl",
    "definition": "def",
}


def weave_stubborn_dsl(
    graph: PrunedGraph,
    *,
    max_tokens: int | None = None,
    options: WeaveOptions | None = None,
) -> WeaveResult:
    """Render pruned symbols as compact Stubborn-DSL v1 (declarations only)."""
    weave_options = options or DEFAULT_WEAVE_OPTIONS
    selected = select_type_symbols(graph.symbols, graph.target_stable_id)
    dropped = 0

    if max_tokens is not None:
        selected, dropped = trim_for_token_budget(
            selected,
            graph,
            max_tokens,
            weave_stubborn_dsl,
            options=weave_options,
        )

    target_type_id = resolve_target_type_id(graph.target_stable_id)
    selected_type_ids = {symbol.stable_id for symbol in selected if kind_bucket(symbol) == "type"}
    javadoc_level = weave_options.effective_javadoc("stubborn-dsl")

    target_label = short_target_name(graph.target_stable_id)
    lines: list[str] = [
        f"stubborn-dsl/{_STUBBORN_DSL_VERSION}",
        *LLM_GUIDE_LINES,
        f"target {target_label}",
        "policy declarations-only",
        "",
    ]

    target_symbol = next(
        (s for s in graph.symbols if s.stable_id == graph.target_stable_id),
        None,
    )
    if target_symbol is not None and _is_method_like(target_symbol):
        member_line = _format_member_line(target_symbol)
        if member_line:
            lines.append(member_line)
            lines.append("")

    type_symbols = [s for s in selected if kind_bucket(s) == "type"]

    if type_symbols:
        lines.append("types:")
        for symbol in sorted(type_symbols, key=sort_key):
            type_line = _format_type_line(symbol)
            if type_line:
                lines.append(f"  {type_line}")
            lines.extend(format_stubborn_dsl_doc_lines(symbol.documentation, javadoc_level))
        lines.append("")

    member_lines: list[str] = []
    for symbol in sorted(type_symbols, key=sort_key):
        if not type_includes_method_signatures(
            symbol.stable_id,
            target_type_id=target_type_id,
            mode=weave_options.member_signatures,
            selected_type_ids=selected_type_ids,
        ):
            continue
        for method in method_members_for_type(graph.symbols, symbol.stable_id):
            label = short_target_name(method.stable_id)
            sig = normalize_method_signature(method)
            member_lines.append(f"  m {label} {sig}")

    if member_lines:
        lines.append("members:")
        lines.extend(member_lines)
        lines.append("")

    stable_ids = {s.stable_id for s in selected}
    if target_symbol is not None and _is_method_like(target_symbol):
        stable_ids.add(target_symbol.stable_id)

    pruned_edges = [edge for edge in graph.edges if edge[0] in stable_ids and edge[1] in stable_ids]
    if pruned_edges:
        lines.append("edges:")
        for from_id, to_id, edge_kind in sorted(pruned_edges):
            abbrev = _EDGE_ABBREV.get(edge_kind, edge_kind)
            lines.append(f"  {abbrev} {short_target_name(from_id)} -> {short_target_name(to_id)}")
        lines.append("")

    graph_stable_ids = {symbol.stable_id for symbol in graph.symbols}
    contract_edges = [
        edge
        for edge in graph.contract_edges
        if edge.from_stable_id in graph_stable_ids and edge.to_stable_id in graph_stable_ids
    ]
    contract_endpoints = {endpoint.stable_id: endpoint for endpoint in graph.contract_endpoints}
    contract_endpoint_ids = set(contract_endpoints) | {
        edge.endpoint_stable_id for edge in contract_edges
    }
    if contract_endpoint_ids:
        lines.append("contracts:")
        for endpoint_id in sorted(contract_endpoint_ids):
            endpoint = contract_endpoints.get(endpoint_id)
            edges = [
                edge for edge in contract_edges if edge.endpoint_stable_id == endpoint_id
            ]
            protocol = endpoint.protocol if endpoint is not None else edges[0].protocol
            lines.append(f"  {protocol} {endpoint_id}")
            if endpoint is not None:
                for constraint in endpoint.schema_constraints:
                    lines.append(_format_contract_schema_constraint(constraint))
            for edge in sorted(edges, key=_contract_sort_key):
                lines.append(_format_contract_edge(edge))
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    return WeaveResult(
        text=text,
        symbol_count=len(selected) + (1 if target_symbol and _is_method_like(target_symbol) else 0),
        estimated_tokens=estimate_tokens(text),
        dropped_for_budget=dropped,
    )


def _is_method_like(symbol: PrunedSymbol) -> bool:
    kind = (symbol.kind or "").lower()
    if kind in _METHOD_KINDS:
        return True
    if "#" in symbol.stable_id:
        member = symbol.stable_id.split("#", 1)[1]
        return "(" in member
    return False


def _kind_code(symbol: PrunedSymbol) -> str:
    kind = (symbol.kind or "").lower()
    if kind in _KIND_CODES:
        return _KIND_CODES[kind]
    signature = (symbol.signature or "").lower()
    for keyword, code in _KIND_CODES.items():
        if keyword in signature:
            return code
    return "c"


def _extract_annotations(signature: str) -> str:
    return " ".join(_ANNOTATION_RE.findall(signature))


def _extract_type_name(symbol: PrunedSymbol) -> str:
    signature = symbol.signature or ""
    match = _TYPE_DECL_RE.search(signature)
    if match:
        return match.group(2)
    return symbol.display_name or short_name(symbol.stable_id).split("(", 1)[0] or "Unknown"


def _normalize_signature(signature: str) -> str:
    text = " ".join(signature.split())
    for prefix in ("public ", "protected ", "private ", "static ", "final ", "abstract "):
        while text.startswith(prefix):
            text = text[len(prefix) :]
    return text


def _format_type_line(symbol: PrunedSymbol) -> str | None:
    if is_annotation_only(symbol):
        return None

    name = _extract_type_name(symbol)
    code = _kind_code(symbol)
    annotations = _extract_annotations(symbol.signature or "")
    if annotations:
        return f"{code} {name} {annotations}".rstrip()
    return f"{code} {name}"


def _format_member_line(symbol: PrunedSymbol) -> str | None:
    if (symbol.kind or "").lower() == "constructor":
        return None

    signature = _normalize_signature((symbol.signature or "").strip())
    if not signature:
        name = short_target_name(symbol.stable_id)
        return f"member m {name}"

    label = short_target_name(symbol.stable_id)
    return f"member m {label} {signature}"


def _contract_sort_key(edge: ContractPrunedEdge) -> tuple[str, str, str, str]:
    return (
        edge.endpoint_stable_id,
        edge.from_role,
        edge.from_stable_id,
        edge.to_stable_id,
    )


def _format_contract_schema_constraint(
    constraint: PrunedContractSchemaConstraint,
) -> str:
    field = (
        constraint.location
        if not constraint.field_path
        else f"{constraint.location}.{constraint.field_path}"
    )
    type_name = constraint.type_name or "unknown"
    required = ""
    if constraint.required is not None:
        required = " required" if constraint.required else " optional"
    return f"    schema {field} {type_name}{required}"


def _format_contract_edge(edge: ContractPrunedEdge) -> str:
    return (
        f"    {edge.from_role} {short_target_name(edge.from_stable_id)}"
        f" -> {edge.to_role} {short_target_name(edge.to_stable_id)}"
        f" evidence={edge.evidence}"
    )
