#!/usr/bin/env python3
"""Verify demo-spring OrderService context includes expected type neighbors."""

from __future__ import annotations

import sys
from pathlib import Path

from stubborn.api import get_context

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "examples" / "demo-spring"
DB_PATH = DEMO_ROOT / "metadata" / "symbols.db"
EXPECTED_PATH = DEMO_ROOT / "metadata" / "expected-context-types.txt"
TARGET = (
    "semanticdb maven maven/com.example/orders-demo 0.1.0-SNAPSHOT "
    "com/example/orders/service/OrderService#"
)


def main() -> int:
    if not DB_PATH.exists():
        print(f"Missing symbol graph: {DB_PATH}", file=sys.stderr)
        print("Run examples/demo-spring/scripts/run-e2e.ps1 or docker compose run --rm e2e", file=sys.stderr)
        return 1

    required = [
        line.strip()
        for line in EXPECTED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = get_context(TARGET, db_path=DB_PATH)
    missing = [name for name in required if name not in result.text]

    print(f"target: {TARGET}")
    print(f"symbols: {result.symbol_count}")
    print(f"tokens_est: {result.estimated_tokens}")

    if missing:
        print("missing types in context:", ", ".join(missing), file=sys.stderr)
        return 1

    print(f"OK — all {len(required)} expected types present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
