"""Direct coverage for small ingest/weave helper modules."""

from __future__ import annotations

from stubborn.ingest.models import EdgeRecord, IndexSnapshot, SymbolRecord
from stubborn.ingest.ndjson import parse_ndjson_index
from stubborn.ingest.paths import filter_snapshot_by_paths, resolve_merge_paths
from stubborn.weave.stubborn_dsl_llm import llm_guide_text


def test_paths_helpers_preserve_snapshot_metadata() -> None:
    snapshot = IndexSnapshot(
        scip_source="fixture.json",
        project_root="/workspace/demo",
        language="java",
        symbols=[
            SymbolRecord(
                stable_id="semanticdb maven com/example/Foo#",
                display_name="Foo",
                kind="class",
                relative_path="src/Foo.java",
            ),
            SymbolRecord(
                stable_id="semanticdb maven com/example/Foo#bar().",
                display_name="bar",
                kind="method",
                relative_path="src/Foo.java",
            ),
            SymbolRecord(
                stable_id="semanticdb maven com/example/Baz#",
                display_name="Baz",
                kind="class",
                relative_path="src/Baz.java",
            ),
        ],
        edges=[
            EdgeRecord(
                from_stable_id="semanticdb maven com/example/Foo#bar().",
                to_stable_id="semanticdb maven com/example/Baz#",
                edge_kind="reference",
            )
        ],
    )

    assert resolve_merge_paths(snapshot, None) == {"src/Baz.java", "src/Foo.java"}
    assert resolve_merge_paths(snapshot, {"src/Foo.java", ""}) == {"src/Foo.java"}

    filtered = filter_snapshot_by_paths(snapshot, {"src/Foo.java"})
    assert filtered.project_root == "/workspace/demo"
    assert filtered.language == "java"
    assert [symbol.display_name for symbol in filtered.symbols] == ["Foo", "bar"]
    assert len(filtered.edges) == 1


def test_ndjson_parser_accepts_metadata_only_line() -> None:
    parsed = parse_ndjson_index('{"metadata": {}}\n')

    assert parsed.metadata is not None
    assert parsed.documents == []
    assert parsed.external_symbols == []


def test_stubborn_dsl_llm_guide_text_stays_concise() -> None:
    guide = llm_guide_text()

    assert "pruned dependency graphs" in guide
    assert "No method bodies." in guide
