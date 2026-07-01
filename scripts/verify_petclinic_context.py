#!/usr/bin/env python3
"""Verify spring-petclinic VetController context neighbors and compression KPI."""

from __future__ import annotations

import sys
from pathlib import Path

from stubborn.api import get_context, get_metrics
from stubborn.store.reader import resolve_stable_id

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "spring-petclinic"
DB_PATH = EXAMPLE_ROOT / "metadata" / "symbols.db"
JAVA_ROOT = EXAMPLE_ROOT / "upstream" / "src" / "main" / "java"
EXPECTED_PATH = EXAMPLE_ROOT / "metadata" / "expected-context-types-vet-controller.txt"
TARGET_DISPLAY = "VetController"
MIN_SAVINGS_PERCENT = 70.0


def main() -> int:
    if not DB_PATH.exists():
        print(f"Missing symbol graph: {DB_PATH}", file=sys.stderr)
        print(
            "Run: docker compose run --rm petclinic-e2e",
            file=sys.stderr,
        )
        return 1

    if not EXPECTED_PATH.exists():
        print(f"Missing expected types file: {EXPECTED_PATH}", file=sys.stderr)
        return 1

    target = resolve_stable_id(DB_PATH, display_name=TARGET_DISPLAY)
    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    context = get_context(target, db_path=DB_PATH)
    missing = [name for name in required if name not in context.text]

    sources = JAVA_ROOT
    if not sources.exists():
        sources = Path("/petclinic/src/main/java")
    if not sources.exists():
        print("warning: Java sources not found for metrics; using graph-only checks", file=sys.stderr)
        metrics = None
    else:
        metrics = get_metrics(target, sources, db_path=DB_PATH)

    print(f"target: {target}")
    print(f"symbols: {context.symbol_count}")
    print(f"tokens_est: {context.estimated_tokens}")
    if metrics:
        print(f"source_files: {metrics['source_files']}")
        print(f"token_savings_percent: {metrics['token_savings_percent']}")

    if missing:
        print("missing types in context:", ", ".join(missing), file=sys.stderr)
        return 1

    if metrics and metrics["token_savings_percent"] < MIN_SAVINGS_PERCENT:
        print(
            f"token savings below floor ({MIN_SAVINGS_PERCENT}%): "
            f"{metrics['token_savings_percent']}",
            file=sys.stderr,
        )
        return 1

    print(f"OK — all {len(required)} expected types present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
