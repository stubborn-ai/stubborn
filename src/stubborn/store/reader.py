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


def _placeholders(values: list[object]) -> str:
    return ",".join("?" * len(values))


def latest_index_run_ids(
    conn: sqlite3.Connection,
    *,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[int]:
    """Resolve the active run set for legacy, repo, or workspace scoped queries."""
    if index_run_id is not None:
        return [index_run_id]

    if repo_key is not None:
        sql = """
            SELECT ir.id
            FROM index_run ir
            JOIN repo r ON r.id = ir.repo_id
            JOIN workspace w ON w.id = r.workspace_id
            WHERE r.repo_key = ?
        """
        params: list[object] = [repo_key]
        if workspace is not None:
            sql += " AND w.name = ?"
            params.append(workspace)
        sql += " ORDER BY ir.id DESC LIMIT 1"
        row = conn.execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"No index runs found for repo {repo_key!r}")
        return [int(row[0])]

    if workspace is not None:
        rows = conn.execute(
            """
            SELECT MAX(ir.id) AS run_id
            FROM index_run ir
            JOIN repo r ON r.id = ir.repo_id
            JOIN workspace w ON w.id = r.workspace_id
            WHERE w.name = ?
            GROUP BY r.id
            ORDER BY r.priority, r.repo_key
            """,
            (workspace,),
        ).fetchall()
        if not rows:
            raise ValueError(f"No index runs found for workspace {workspace!r}")
        return [int(row[0]) for row in rows]

    return [_latest_index_run_id(conn, None)]


def list_symbols(
    db_path: str | Path,
    *,
    query: str | None = None,
    kind: str | None = None,
    limit: int = 50,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[SymbolSummary]:
    """List symbols from the latest legacy run or a scoped workspace/repo view."""
    if limit < 1:
        raise ValueError("limit must be >= 1")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_ids = latest_index_run_ids(
            conn,
            index_run_id=index_run_id,
            workspace=workspace,
            repo_key=repo_key,
        )
        placeholders = _placeholders(list(run_ids))
        sql = (
            """
            SELECT stable_id, display_name, kind, signature, documentation
            FROM scip_symbol
            WHERE index_run_id IN (
        """
            + placeholders
            + ")"
        )
        params: list[object] = list(run_ids)

        if query:
            pattern = f"%{query}%"
            sql += " AND (stable_id LIKE ? OR display_name LIKE ? OR signature LIKE ?)"
            params.extend([pattern, pattern, pattern])

        if kind:
            sql += " AND kind = ?"
            params.append(kind)

        sql += """
            ORDER BY stable_id,
                     CASE WHEN relative_path IS NULL THEN 1 ELSE 0 END,
                     index_run_id DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        summaries: list[SymbolSummary] = []
        seen: set[str] = set()
        for row in rows:
            if row["stable_id"] in seen:
                continue
            seen.add(row["stable_id"])
            summaries.append(
                SymbolSummary(
                    stable_id=row["stable_id"],
                    display_name=row["display_name"],
                    kind=row["kind"],
                    signature=row["signature"],
                    documentation=row["documentation"],
                )
            )
        return summaries
    finally:
        conn.close()


def resolve_stable_id(
    db_path: str | Path,
    *,
    display_name: str,
    prefer_type: bool = True,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> str:
    """Resolve a symbol stable_id by display name (prefers type-level symbols)."""
    conn = sqlite3.connect(db_path)
    try:
        run_ids = latest_index_run_ids(
            conn,
            index_run_id=index_run_id,
            workspace=workspace,
            repo_key=repo_key,
        )
        placeholders = _placeholders(list(run_ids))
        rows = conn.execute(
            f"""
            SELECT stable_id, kind
            FROM scip_symbol
            WHERE index_run_id IN ({placeholders})
              AND (display_name = ? OR stable_id LIKE ?)
            ORDER BY CASE WHEN relative_path IS NULL THEN 1 ELSE 0 END,
                     length(stable_id),
                     stable_id
            """,
            (*run_ids, display_name, f"%{display_name}#%"),
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
