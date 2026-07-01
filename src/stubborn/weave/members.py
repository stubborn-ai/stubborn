"""Method signature helpers for weavers (v0.9)."""

from __future__ import annotations

from stubborn.graph.prune import PrunedSymbol
from stubborn.weave._shared import sort_key

_METHOD_KINDS = frozenset({"method", "abstractmethod", "staticmethod"})


def enclosing_type_stable_id(stable_id: str) -> str | None:
    if not stable_id.endswith("#") and "#" in stable_id:
        return stable_id.split("#", 1)[0] + "#"
    if stable_id.endswith("#"):
        return stable_id
    return None


def is_constructor_symbol(symbol: PrunedSymbol) -> bool:
    if (symbol.kind or "").lower() == "constructor":
        return True
    return "<init>" in symbol.stable_id or symbol.display_name == "<init>"


def is_method_symbol(symbol: PrunedSymbol) -> bool:
    kind = (symbol.kind or "").lower()
    if kind in _METHOD_KINDS:
        return True
    if "#" not in symbol.stable_id:
        return False
    member = symbol.stable_id.split("#", 1)[1]
    return "(" in member and not is_constructor_symbol(symbol)


def method_members_for_type(
    symbols: list[PrunedSymbol],
    type_stable_id: str,
) -> list[PrunedSymbol]:
    if not type_stable_id.endswith("#"):
        return []
    return sorted(
        [
            symbol
            for symbol in symbols
            if symbol.stable_id.startswith(type_stable_id)
            and symbol.stable_id != type_stable_id
            and is_method_symbol(symbol)
        ],
        key=sort_key,
    )


def normalize_method_signature(symbol: PrunedSymbol) -> str:
    signature = (symbol.signature or "").strip()
    if not signature:
        name = symbol.display_name or symbol.stable_id.split("#", 1)[-1]
        return f"void {name}()"
    text = " ".join(signature.split())
    if text.endswith(";"):
        return text[:-1].strip()
    if text.endswith("}"):
        return text
    return text


def resolve_target_type_id(target_stable_id: str) -> str | None:
    if target_stable_id.endswith("#"):
        return target_stable_id
    if "#" in target_stable_id:
        return target_stable_id.split("#", 1)[0] + "#"
    return None


def type_includes_method_signatures(
    type_stable_id: str,
    *,
    target_type_id: str | None,
    mode: str,
    selected_type_ids: set[str],
) -> bool:
    if mode == "off" or not type_stable_id.endswith("#"):
        return False
    if type_stable_id not in selected_type_ids:
        return False
    if mode == "all":
        return True
    if mode == "target":
        return type_stable_id == target_type_id
    if mode == "neighbors":
        return type_stable_id != target_type_id
    raise ValueError(f"Unsupported member_signatures mode: {mode!r}")


def _strip_javadoc_line(line: str) -> str:
    return (
        line.strip()
        .removeprefix("/**")
        .removeprefix("*/")
        .removeprefix("*")
        .removesuffix("*/")
        .strip()
    )


def javadoc_first_line(documentation: str | None) -> str | None:
    if not documentation:
        return None
    for line in documentation.splitlines():
        stripped = _strip_javadoc_line(line)
        if stripped and not stripped.startswith("@"):
            return stripped
    return None


def javadoc_lines(documentation: str | None, level: str) -> list[str]:
    if level == "off" or not documentation:
        return []
    if level == "summary":
        line = javadoc_first_line(documentation)
        return [line] if line else []
    return [
        stripped for line in documentation.splitlines() if (stripped := _strip_javadoc_line(line))
    ]


def format_java_javadoc_prefix(documentation: str | None, level: str) -> str:
    lines = [f"// {line}" for line in javadoc_lines(documentation, level)]
    return "\n".join(lines) + ("\n" if lines else "")


def quote_stubborn_dsl_doc(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_stubborn_dsl_doc_lines(documentation: str | None, level: str) -> list[str]:
    return [f"  doc {quote_stubborn_dsl_doc(line)}" for line in javadoc_lines(documentation, level)]
