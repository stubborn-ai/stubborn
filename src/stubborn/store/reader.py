"""Read symbol graph data from SQLite."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymbolSummary:
    """Symbol row returned from list/browse queries (read model)."""

    stable_id: str
    display_name: str | None
    kind: str | None
    signature: str | None
    documentation: str | None


def resolve_db_path(db_path: str | Path | None) -> Path:
    """Resolve DB path from argument or STUBBORN_DB environment variable."""
    if db_path is not None:
        path = Path(db_path)
    else:
        env = os.environ.get("STUBBORN_DB")
        if not env:
            raise ValueError(
                "db_path is required (or set STUBBORN_DB to the symbol graph SQLite file)"
            )
        path = Path(env)
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _latest_index_run_id(conn: sqlite3.Connection, index_run_id: int | None) -> int:
    if index_run_id is not None:
        return index_run_id
    row = conn.execute("SELECT id FROM index_run ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        raise ValueError("No index runs found in database")
    return int(row[0])


def list_symbols(
    db_path: str | Path,
    *,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    index_run_id: int | None = None,
) -> list[SymbolSummary]:
    """List symbols from the latest (or specific) index run."""
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_id = _latest_index_run_id(conn, index_run_id)
        sql = """
            SELECT stable_id, display_name, kind, signature, documentation
            FROM scip_symbol
            WHERE index_run_id = ?
        """
        params: list[object] = [run_id]

        if query:
            pattern = f"%{query}%"
            sql += " AND (stable_id LIKE ? OR display_name LIKE ? OR signature LIKE ?)"
            params.extend([pattern, pattern, pattern])

        if kind:
            sql += " AND kind = ?"
            params.append(kind)

        sql += " ORDER BY stable_id LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [
            SymbolSummary(
                stable_id=row["stable_id"],
                display_name=row["display_name"],
                kind=row["kind"],
                signature=row["signature"],
                documentation=row["documentation"],
            )
            for row in rows
        ]
    finally:
        conn.close()


def resolve_stable_id(
    db_path: str | Path,
    *,
    display_name: str,
    prefer_type: bool = True,
    index_run_id: int | None = None,
) -> str:
    """Resolve a symbol stable_id by display name (prefers type-level symbols)."""
    conn = sqlite3.connect(db_path)
    try:
        run_id = _latest_index_run_id(conn, index_run_id)
        rows = conn.execute(
            """
            SELECT stable_id, kind
            FROM scip_symbol
            WHERE index_run_id = ?
              AND (display_name = ? OR stable_id LIKE ?)
            ORDER BY length(stable_id)
            """,
            (run_id, display_name, f"%{display_name}#%"),
        ).fetchall()
        if not rows:
            raise ValueError(f"Symbol not found: {display_name!r}")

        if prefer_type:
            for stable_id, kind in rows:
                if stable_id.endswith("#") or (kind or "").lower() in (
                    "class",
                    "interface",
                    "enum",
                    "record",
                ):
                    return stable_id
        return rows[0][0]
    finally:
        conn.close()
