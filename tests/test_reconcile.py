"""Tests for symbol reconcile."""

from __future__ import annotations

from stubborn.reconcile.diff import format_report, reconcile
from stubborn.reconcile.entities import SymbolEntity


def test_reconcile_ok() -> None:
    expected = {SymbolEntity("a"), SymbolEntity("b")}
    actual = {SymbolEntity("a"), SymbolEntity("b")}
    report = reconcile(expected, actual)
    assert report.ok
    assert report.matched == 2


def test_reconcile_missing() -> None:
    expected = {SymbolEntity("a"), SymbolEntity("b")}
    actual = {SymbolEntity("a")}
    report = reconcile(expected, actual)
    assert not report.ok
    assert len(report.missing) == 1
    assert report.missing[0].stable_id == "b"
    assert "[Error] Missing mapping for node: b" in format_report(report)
