"""Write SCIP-derived symbol graphs to SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from stubborn import __version__
from stubborn.ingest.models import IndexSnapshot
from stubborn.ingest.paths import filter_snapshot_by_paths, resolve_merge_paths


def _schema_path(name: str) -> str:
    ref = resources.files("stubborn.store") / "schema" / name
    with resources.as_file(ref) as path:
        return str(path)


def _schema_version(conn: sqlite3.Connection) -> int | None:
    try:
        row = conn.execute("SELECT MAX(version) FROM meta_schema_version").fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])
    except sqlite3.OperationalError:
        return None


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create or upgrade schema to v2."""
    version = _schema_version(conn)
    if version is None:
        with open(_schema_path("v2.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        return
    if version < 2:
        with open(_schema_path("migrate_v1_to_v2.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())


def init_db(db_path: str | Path) -> None:
    """Create or upgrade SQLite file with symbol graph DDL."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        ensure_schema(conn)
        conn.commit()
    finally:
        conn.close()


@dataclass
class IndexInfo:
    index_run_id: int
    scip_source: str
    language: str | None
    indexed_at: str
    symbol_count: int
    edge_count: int
    mode: str = "snapshot"
    merge_count: int = 0


def read_info(db_path: str | Path, index_run_id: int | None = None) -> IndexInfo:
    """Read summary for latest or specific index run."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        conn.commit()

        if index_run_id is None:
            row = conn.execute("SELECT id FROM index_run ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                raise ValueError(f"No index runs found in {db_path}")
            index_run_id = row["id"]

        run = conn.execute(
            """
            SELECT id, scip_source, language, indexed_at, mode, merge_count
            FROM index_run WHERE id = ?
            """,
            (index_run_id,),
        ).fetchone()
        if run is None:
            raise ValueError(f"index_run {index_run_id} not found in {db_path}")

        symbol_count = conn.execute(
            "SELECT COUNT(*) FROM scip_symbol WHERE index_run_id = ?",
            (index_run_id,),
        ).fetchone()[0]
        edge_count = conn.execute(
            "SELECT COUNT(*) FROM scip_edge WHERE index_run_id = ?",
            (index_run_id,),
        ).fetchone()[0]

        return IndexInfo(
            index_run_id=run["id"],
            scip_source=run["scip_source"],
            language=run["language"],
            indexed_at=run["indexed_at"],
            symbol_count=symbol_count,
            edge_count=edge_count,
            mode=run["mode"] or "snapshot",
            merge_count=int(run["merge_count"] or 0),
        )
    finally:
        conn.close()


class IndexWriter:
    """Persist an in-memory index snapshot to SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            init_db(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        ensure_schema(conn)
        conn.commit()
        return conn

    def write(self, snapshot: IndexSnapshot) -> int:
        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO index_run (
                    project_root, scip_source, scip_hash, language, tool_version,
                    mode, merge_count
                ) VALUES (?, ?, ?, ?, ?, 'snapshot', 0)
                """,
                (
                    snapshot.project_root,
                    snapshot.scip_source,
                    snapshot.scip_hash,
                    snapshot.language,
                    __version__,
                ),
            )
            index_run_id = cursor.lastrowid
            assert index_run_id is not None
            self._insert_symbols_and_edges(conn, index_run_id, snapshot)
            conn.commit()
            return index_run_id
        finally:
            conn.close()

    def merge(self, snapshot: IndexSnapshot, *, paths: set[str] | None = None) -> int:
        """Update the latest index run with path-scoped symbol/edge replacement."""
        merge_paths = resolve_merge_paths(snapshot, paths)
        filtered = filter_snapshot_by_paths(snapshot, merge_paths)

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, merge_count FROM index_run ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO index_run (
                        project_root, scip_source, scip_hash, language, tool_version,
                        mode, merge_count
                    ) VALUES (?, ?, ?, ?, ?, 'merged', 0)
                    """,
                    (
                        snapshot.project_root,
                        snapshot.scip_source,
                        snapshot.scip_hash,
                        snapshot.language,
                        __version__,
                    ),
                )
                index_run_id = cursor.lastrowid
                assert index_run_id is not None
            else:
                index_run_id = int(row[0])
                merge_count = int(row[1] or 0) + 1
                conn.execute(
                    """
                    UPDATE index_run
                    SET scip_source = ?, scip_hash = ?, language = ?,
                        indexed_at = datetime('now'), tool_version = ?,
                        mode = 'merged', merge_count = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.scip_source,
                        snapshot.scip_hash,
                        snapshot.language,
                        __version__,
                        merge_count,
                        index_run_id,
                    ),
                )

            if merge_paths:
                placeholders = ",".join("?" * len(merge_paths))
                symbol_rows = conn.execute(
                    f"""
                    SELECT id FROM scip_symbol
                    WHERE index_run_id = ? AND relative_path IN ({placeholders})
                    """,
                    (index_run_id, *sorted(merge_paths)),
                ).fetchall()
                symbol_ids = [int(r[0]) for r in symbol_rows]
                if symbol_ids:
                    id_placeholders = ",".join("?" * len(symbol_ids))
                    conn.execute(
                        f"""
                        DELETE FROM scip_edge
                        WHERE index_run_id = ?
                          AND (from_symbol_id IN ({id_placeholders})
                               OR to_symbol_id IN ({id_placeholders}))
                        """,
                        (index_run_id, *symbol_ids, *symbol_ids),
                    )
                    conn.execute(
                        f"""
                        DELETE FROM scip_symbol
                        WHERE index_run_id = ? AND id IN ({id_placeholders})
                        """,
                        (index_run_id, *symbol_ids),
                    )

            self._insert_symbols_and_edges(conn, index_run_id, filtered)
            conn.commit()
            return index_run_id
        finally:
            conn.close()

    def _insert_symbols_and_edges(
        self,
        conn: sqlite3.Connection,
        index_run_id: int,
        snapshot: IndexSnapshot,
    ) -> None:
        symbol_ids: dict[str, int] = {}
        for symbol in snapshot.symbols:
            row = conn.execute(
                """
                INSERT INTO scip_symbol (
                    index_run_id, stable_id, display_name, kind,
                    signature, documentation, relative_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    index_run_id,
                    symbol.stable_id,
                    symbol.display_name,
                    symbol.kind,
                    symbol.signature,
                    symbol.documentation,
                    symbol.relative_path,
                ),
            )
            symbol_ids[symbol.stable_id] = row.lastrowid

        edge_stable_ids = {
            stable_id
            for edge in snapshot.edges
            for stable_id in (edge.from_stable_id, edge.to_stable_id)
            if stable_id not in symbol_ids
        }
        if edge_stable_ids:
            placeholders = ",".join("?" * len(edge_stable_ids))
            rows = conn.execute(
                f"""
                SELECT stable_id, id
                FROM scip_symbol
                WHERE index_run_id = ? AND stable_id IN ({placeholders})
                """,
                (index_run_id, *sorted(edge_stable_ids)),
            ).fetchall()
            symbol_ids.update({stable_id: int(symbol_id) for stable_id, symbol_id in rows})

        for edge in snapshot.edges:
            from_id = symbol_ids.get(edge.from_stable_id)
            to_id = symbol_ids.get(edge.to_stable_id)
            if from_id is None or to_id is None:
                continue
            conn.execute(
                """
                INSERT INTO scip_edge (
                    index_run_id, from_symbol_id, to_symbol_id, edge_kind
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(index_run_id, from_symbol_id, to_symbol_id, edge_kind)
                DO NOTHING
                """,
                (index_run_id, from_id, to_id, edge.edge_kind),
            )
