"""Shared symbol selection and budget trimming for weavers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from stubborn.weave.options import DEFAULT_WEAVE_OPTIONS, WeaveOptions
from stubborn.weave.types import WeaveResult

if TYPE_CHECKING:
    from stubborn.graph.prune import PrunedGraph, PrunedSymbol

_TYPE_KINDS = frozenset({"class", "interface", "enum", "record"})


def short_name(stable_id: str) -> str:
    if " " in stable_id:
        return stable_id.split(" ", 1)[1]
    if "#" in stable_id:
        return stable_id.split("#", 1)[-1] or stable_id
    return stable_id


def short_target_name(stable_id: str) -> str:
    """Human-readable target label (Type or Type.member)."""
    if "#" not in stable_id:
        return short_name(stable_id)

    type_path, member = stable_id.split("#", 1)
    type_name = type_path.rsplit("/", 1)[-1]
    if not member:
        return type_name

    member_name = member.split("(", 1)[0].rstrip(".")
    if member_name in ("", "<init>"):
        return type_name if member_name == "" else f"{type_name}.<init>"
    return f"{type_name}.{member_name}"


def kind_bucket(symbol: PrunedSymbol) -> str:
    kind = (symbol.kind or "").lower()
    if kind in _TYPE_KINDS or symbol.stable_id.endswith("#"):
        return "type"
    return "member"


def is_annotation_only(symbol: PrunedSymbol) -> bool:
    signature = (symbol.signature or "").strip()
    if not signature.startswith("@"):
        return False
    lowered = signature.lower()
    return not any(
        keyword in lowered
        for keyword in (" class ", " interface ", " enum ", " record ", "class ", "\nclass ")
    )


def is_enum_constant(symbol: PrunedSymbol) -> bool:
    if not symbol.stable_id.endswith("#"):
        return False
    suffix = symbol.stable_id.split("#", 1)[-1]
    return bool(suffix)


def select_type_symbols(symbols: list[PrunedSymbol], target_stable_id: str) -> list[PrunedSymbol]:
    selected: list[PrunedSymbol] = []
    for symbol in symbols:
        if is_annotation_only(symbol):
            continue
        if kind_bucket(symbol) != "type":
            continue
        if is_enum_constant(symbol):
            continue
        selected.append(symbol)

    if not any(s.stable_id == target_stable_id for s in selected):
        for symbol in symbols:
            if symbol.stable_id == target_stable_id:
                selected.insert(0, symbol)
                break

    return selected


def sort_key(symbol: PrunedSymbol) -> tuple[int, str]:
    return (symbol.depth, symbol.stable_id)


def trim_for_token_budget(
    symbols: list[PrunedSymbol],
    graph: PrunedGraph,
    max_tokens: int,
    weave_fn: Callable[..., WeaveResult],
    *,
    options: WeaveOptions | None = None,
) -> tuple[list[PrunedSymbol], int]:
    weave_options = options or DEFAULT_WEAVE_OPTIONS
    selected = list(symbols)
    dropped = 0
    target_id = graph.target_stable_id

    while selected:
        preview = weave_fn(
            type(graph)(
                target_stable_id=graph.target_stable_id,
                symbols=selected,
                edges=graph.edges,
            ),
            max_tokens=None,
            options=weave_options,
        )
        if preview.estimated_tokens <= max_tokens:
            return selected, dropped

        removable = [s for s in selected if s.stable_id != target_id]
        if not removable:
            return selected, dropped

        removable.sort(key=lambda s: (-s.depth, s.stable_id))
        selected.remove(removable[0])
        dropped += 1

    return selected, dropped
