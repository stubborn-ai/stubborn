"""Write SCIP-derived symbol graphs to SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from stubborn import __version__
from stubborn.ingest.models import IndexSnapshot


def _schema_sql_path() -> str:
    ref = resources.files("stubborn.store") / "schema" / "v1.sql"
    with resources.as_file(ref) as path:
        return str(path)


def init_db(db_path: str | Path) -> None:
    """Create or upgrade SQLite file with symbol graph DDL."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        with open(_schema_sql_path(), encoding="utf-8") as f:
            conn.executescript(f.read())
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


def read_info(db_path: str | Path, index_run_id: int | None = None) -> IndexInfo:
    """Read summary for latest or specific index run."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if index_run_id is None:
            row = conn.execute("SELECT id FROM index_run ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                raise ValueError(f"No index runs found in {db_path}")
            index_run_id = row["id"]

        run = conn.execute(
            "SELECT id, scip_source, language, indexed_at FROM index_run WHERE id = ?",
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
        )
    finally:
        conn.close()


class IndexWriter:
    """Persist an in-memory index snapshot to SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            init_db(self.db_path)

    def write(self, snapshot: IndexSnapshot) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO index_run (
                    project_root, scip_source, scip_hash, language, tool_version
                ) VALUES (?, ?, ?, ?, ?)
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

            symbol_ids: dict[str, int] = {}
            for symbol in snapshot.symbols:
                row = conn.execute(
                    """
                    INSERT INTO scip_symbol (
                        index_run_id, stable_id, display_name, kind,
                        signature, documentation
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        index_run_id,
                        symbol.stable_id,
                        symbol.display_name,
                        symbol.kind,
                        symbol.signature,
                        symbol.documentation,
                    ),
                )
                symbol_ids[symbol.stable_id] = row.lastrowid

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

            conn.commit()
            return index_run_id
        finally:
            conn.close()
