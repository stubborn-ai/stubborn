#!/usr/bin/env python3
"""Verify demo-spring OrderController context includes expected type neighbors."""

from __future__ import annotations

import sys
from pathlib import Path

from stubborn.api import get_context
from stubborn.store.reader import resolve_stable_id

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "demo-spring"
DB_PATH = DEMO_ROOT / "metadata" / "symbols.db"
EXPECTED_PATH = DEMO_ROOT / "metadata" / "expected-context-types-controller.txt"


def main() -> int:
    if not DB_PATH.exists():
        print(f"Missing symbol graph: {DB_PATH}", file=sys.stderr)
        print("Run examples/demo-spring/scripts/run-e2e.ps1 or docker compose run --rm e2e", file=sys.stderr)
        return 1

    target = resolve_stable_id(DB_PATH, display_name="OrderController")
    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = get_context(target, db_path=DB_PATH)
    missing = [name for name in required if name not in result.text]

    print(f"target: {target}")
    print(f"symbols: {result.symbol_count}")
    print(f"tokens_est: {result.estimated_tokens}")

    if missing:
        print("missing types in context:", ", ".join(missing), file=sys.stderr)
        return 1

    print(f"OK — all {len(required)} expected types present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
