"""Compare symbol sets between two index snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field

from stubborn.reconcile.entities import SymbolEntity


@dataclass
class ReconcileReport:
    """Result of reconciling an expected symbol set against an actual set."""

    matched: int
    missing: list[SymbolEntity] = field(default_factory=list)
    extra: list[SymbolEntity] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.extra


def reconcile(
    expected: set[SymbolEntity],
    actual: set[SymbolEntity],
) -> ReconcileReport:
    """Diff two symbol entity sets. Expected is ground truth (e.g. pre-migration)."""
    expected_keys = {e.stable_id for e in expected}
    actual_keys = {e.stable_id for e in actual}

    missing_keys = expected_keys - actual_keys
    extra_keys = actual_keys - expected_keys
    matched = len(expected_keys & actual_keys)

    missing = sorted(
        (SymbolEntity(k) for k in missing_keys),
        key=lambda e: e.stable_id,
    )
    extra = sorted(
        (SymbolEntity(k) for k in extra_keys),
        key=lambda e: e.stable_id,
    )

    return ReconcileReport(matched=matched, missing=missing, extra=extra)


def format_report(report: ReconcileReport) -> str:
    """Human-readable reconcile output for CLI and CI."""
    lines = [
        f"matched: {report.matched}",
        f"missing: {len(report.missing)}",
        f"extra: {len(report.extra)}",
    ]
    for entity in report.missing:
        lines.append(f"[Error] Missing mapping for node: {entity.stable_id}")
    for entity in report.extra:
        lines.append(f"[Warn] Extra symbol not in scope: {entity.stable_id}")
    return "\n".join(lines)
