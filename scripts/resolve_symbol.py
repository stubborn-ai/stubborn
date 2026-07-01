#!/usr/bin/env python3
"""Resolve a SCIP stable_id from a symbol graph by display name."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stubborn.store.reader import resolve_stable_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--display-name", required=True)
    parser.add_argument(
        "--allow-method",
        action="store_true",
        help="Allow method/field symbols when no type match exists",
    )
    args = parser.parse_args()

    try:
        stable_id = resolve_stable_id(
            args.db_path,
            display_name=args.display_name,
            prefer_type=not args.allow_method,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(stable_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
