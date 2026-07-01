"""Normalized symbol entities for set comparison."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolEntity:
    stable_id: str
