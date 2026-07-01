"""Route pruned graphs to the requested output format."""

from __future__ import annotations

from stubborn.graph.prune import PrunedGraph
from stubborn.weave.stubborn_dsl import weave_stubborn_dsl
from stubborn.weave.java_stub import weave_java_stub
from stubborn.weave.options import DEFAULT_WEAVE_OPTIONS, WeaveOptions
from stubborn.weave.types import WeaveResult

SUPPORTED_FORMATS = frozenset({"java-stub", "stubborn-dsl"})


def weave_context(
    graph: PrunedGraph,
    *,
    format: str = "java-stub",
    max_tokens: int | None = None,
    options: WeaveOptions | None = None,
) -> WeaveResult:
    weave_options = options or DEFAULT_WEAVE_OPTIONS
    if format == "java-stub":
        return weave_java_stub(graph, max_tokens=max_tokens, options=weave_options)
    if format == "stubborn-dsl":
        return weave_stubborn_dsl(graph, max_tokens=max_tokens, options=weave_options)
    raise ValueError(f"Unsupported format: {format!r} (choose: {', '.join(sorted(SUPPORTED_FORMATS))})")
