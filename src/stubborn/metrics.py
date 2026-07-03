"""Compression and context size metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stubborn.config import ContextBudget
from stubborn.graph.prune import prune_context
from stubborn.tokens import estimate_tokens
from stubborn.weave.dispatch import weave_context
from stubborn.weave.options import WeaveOptions
from stubborn.weave.types import WeaveResult


@dataclass(frozen=True)
class SourceStats:
    file_count: int
    byte_count: int
    estimated_tokens: int


@dataclass(frozen=True)
class CompressionReport:
    target_stable_id: str
    source: SourceStats
    stub: WeaveResult
    compression_ratio: float
    token_savings_percent: float

    def format_summary(self) -> str:
        return "\n".join(
            [
                f"target:              {self.target_stable_id}",
                f"source_files:        {self.source.file_count}",
                f"source_bytes:        {self.source.byte_count}",
                f"source_tokens_est:   {self.source.estimated_tokens}",
                f"stub_symbols:        {self.stub.symbol_count}",
                f"stub_bytes:          {len(self.stub.text.encode('utf-8'))}",
                f"stub_tokens_est:     {self.stub.estimated_tokens}",
                f"compression_ratio:   {self.compression_ratio:.2%}",
                f"token_savings:       {self.token_savings_percent:.1f}%",
                f"dropped_for_budget:  {self.stub.dropped_for_budget}",
            ]
        )


def collect_source_stats(source_root: str | Path, *, pattern: str = "**/*.java") -> SourceStats:
    root = Path(source_root)
    if not root.exists():
        raise FileNotFoundError(root)

    files = sorted(root.glob(pattern))
    if not files:
        raise ValueError(f"No Java sources matched {pattern!r} under {root}")

    total_bytes = 0
    for path in files:
        total_bytes += path.read_bytes().__len__()

    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)
    return SourceStats(
        file_count=len(files),
        byte_count=total_bytes,
        estimated_tokens=estimate_tokens(text),
    )


def compute_compression(
    db_path: str | Path,
    target_stable_id: str,
    source_root: str | Path,
    *,
    budget: ContextBudget | None = None,
    format: str = "java-stub",
    options: WeaveOptions | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> CompressionReport:
    budget = budget or ContextBudget()
    graph = prune_context(
        db_path,
        target_stable_id,
        budget=budget,
        workspace=workspace,
        repo_key=repo_key,
    )
    stub = weave_context(
        graph,
        format=format,
        max_tokens=budget.max_tokens,
        options=options,
    )
    source = collect_source_stats(source_root)

    if source.estimated_tokens == 0:
        ratio = 0.0
        savings = 0.0
    else:
        ratio = 1.0 - (stub.estimated_tokens / source.estimated_tokens)
        savings = (1.0 - stub.estimated_tokens / source.estimated_tokens) * 100.0

    return CompressionReport(
        target_stable_id=target_stable_id,
        source=source,
        stub=stub,
        compression_ratio=max(0.0, ratio),
        token_savings_percent=max(0.0, savings),
    )
