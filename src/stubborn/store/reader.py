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


@dataclass(frozen=True)
class RepoRunSummary:
    workspace: str
    repo_key: str
    index_run_id: int
    indexed_at: str
    mode: str
    merge_count: int
    run_kind: str
    symbol_count: int
    edge_count: int
    contract_endpoint_count: int
    contract_binding_count: int


@dataclass(frozen=True)
class ContractBindingSummary:
    endpoint_stable_id: str
    endpoint_display_name: str | None
    protocol: str
    service: str | None
    version: str | None
    method_or_verb: str | None
    address: str
    code_stable_id: str
    role: str
    evidence: str
    source: str | None


@dataclass(frozen=True)
class ContractSchemaConstraintSummary:
    location: str
    field_path: str
    type_name: str | None
    required: bool | None


@dataclass(frozen=True)
class ContractEndpointSummary:
    stable_id: str
    display_name: str | None
    protocol: str
    service: str | None
    version: str | None
    method_or_verb: str | None
    address: str
    schema_constraints: tuple[ContractSchemaConstraintSummary, ...] = ()


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


def _latest_index_run_id(
    conn: sqlite3.Connection,
    index_run_id: int | None,
    *,
    run_kind: str | None = None,
) -> int:
    if index_run_id is not None:
        return index_run_id
    sql = "SELECT id FROM index_run"
    params: list[object] = []
    if run_kind is not None:
        sql += " WHERE run_kind = ?"
        params.append(run_kind)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
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
    run_kind: str | None = None,
) -> list[int]:
    """Resolve the active run set for legacy, repo, or workspace scoped queries."""
    if index_run_id is not None:
        return [index_run_id]

    if repo_key is not None:
        sql = """
            SELECT ir.id, ir.run_kind
            FROM index_run ir
            JOIN repo r ON r.id = ir.repo_id
            JOIN workspace w ON w.id = r.workspace_id
            WHERE r.repo_key = ?
        """
        params: list[object] = [repo_key]
        if workspace is not None:
            sql += " AND w.name = ?"
            params.append(workspace)
        if run_kind is not None:
            sql += " AND ir.run_kind = ?"
            params.append(run_kind)
        if run_kind is None:
            sql = f"""
                SELECT MAX(id) AS run_id
                FROM ({sql}) scoped_runs
                GROUP BY run_kind
                ORDER BY run_kind
            """
            rows = conn.execute(sql, params).fetchall()
            if not rows:
                raise ValueError(f"No index runs found for repo {repo_key!r}")
            return [int(row[0]) for row in rows]

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
              AND (? IS NULL OR ir.run_kind = ?)
            GROUP BY r.id, ir.run_kind
            ORDER BY r.priority, r.repo_key, ir.run_kind
            """,
            (workspace, run_kind, run_kind),
        ).fetchall()
        if not rows:
            raise ValueError(f"No index runs found for workspace {workspace!r}")
        return [int(row[0]) for row in rows]

    return [_latest_index_run_id(conn, None, run_kind=run_kind)]


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
            run_kind="code",
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
            run_kind="code",
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


def workspace_run_summaries(db_path: str | Path, *, workspace: str) -> list[RepoRunSummary]:
    """Return latest run summaries for every repo in a workspace."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run_ids = latest_index_run_ids(conn, workspace=workspace)
        placeholders = _placeholders(list(run_ids))
        rows = conn.execute(
            f"""
            SELECT w.name AS workspace, r.repo_key, ir.id AS index_run_id,
                   ir.indexed_at, ir.mode, ir.merge_count, ir.run_kind,
                   (SELECT COUNT(*) FROM scip_symbol s WHERE s.index_run_id = ir.id) AS symbol_count,
                   (SELECT COUNT(*) FROM scip_edge e WHERE e.index_run_id = ir.id) AS edge_count,
                   (
                     SELECT COUNT(*)
                     FROM contract_endpoint ce
                     WHERE ce.index_run_id = ir.id
                   ) AS contract_endpoint_count,
                   (
                     SELECT COUNT(*)
                     FROM contract_binding cb
                     JOIN contract_endpoint ce ON ce.id = cb.endpoint_id
                     WHERE ce.index_run_id = ir.id
                   ) AS contract_binding_count
            FROM index_run ir
            JOIN repo r ON r.id = ir.repo_id
            JOIN workspace w ON w.id = r.workspace_id
            WHERE ir.id IN ({placeholders})
            ORDER BY r.priority, r.repo_key
            """,
            run_ids,
        ).fetchall()
        return [
            RepoRunSummary(
                workspace=row["workspace"],
                repo_key=row["repo_key"],
                index_run_id=int(row["index_run_id"]),
                indexed_at=row["indexed_at"],
                mode=row["mode"],
                merge_count=int(row["merge_count"] or 0),
                run_kind=row["run_kind"],
                symbol_count=int(row["symbol_count"]),
                edge_count=int(row["edge_count"]),
                contract_endpoint_count=int(row["contract_endpoint_count"]),
                contract_binding_count=int(row["contract_binding_count"]),
            )
            for row in rows
        ]
    finally:
        conn.close()


def list_contract_bindings(
    db_path: str | Path,
    *,
    code_stable_id: str | None = None,
    evidence: str | None = None,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[ContractBindingSummary]:
    """List contract bindings from the latest legacy run or scoped workspace view."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        try:
            run_ids = latest_index_run_ids(
                conn,
                index_run_id=index_run_id,
                workspace=workspace,
                repo_key=repo_key,
                run_kind="contract",
            )
        except ValueError:
            return []
        placeholders = _placeholders(list(run_ids))
        sql = f"""
            SELECT ce.stable_id AS endpoint_stable_id,
                   ce.display_name AS endpoint_display_name,
                   ce.protocol,
                   ce.service,
                   ce.version,
                   ce.method_or_verb,
                   ce.address,
                   cb.code_stable_id,
                   cb.role,
                   cb.evidence,
                   cb.source
            FROM contract_binding cb
            JOIN contract_endpoint ce ON ce.id = cb.endpoint_id
            WHERE ce.index_run_id IN ({placeholders})
        """
        params: list[object] = list(run_ids)

        if code_stable_id is not None:
            sql += " AND cb.code_stable_id = ?"
            params.append(code_stable_id)
        if evidence is not None:
            sql += " AND cb.evidence = ?"
            params.append(evidence)

        sql += " ORDER BY ce.stable_id, cb.role, cb.code_stable_id"

        return [
            ContractBindingSummary(
                endpoint_stable_id=row["endpoint_stable_id"],
                endpoint_display_name=row["endpoint_display_name"],
                protocol=row["protocol"],
                service=row["service"],
                version=row["version"],
                method_or_verb=row["method_or_verb"],
                address=row["address"],
                code_stable_id=row["code_stable_id"],
                role=row["role"],
                evidence=row["evidence"],
                source=row["source"],
            )
            for row in conn.execute(sql, params)
        ]
    finally:
        conn.close()


def list_contract_endpoints(
    db_path: str | Path,
    *,
    query: str | None = None,
    index_run_id: int | None = None,
    workspace: str | None = None,
    repo_key: str | None = None,
) -> list[ContractEndpointSummary]:
    """List contract endpoints, including endpoints with no code bindings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        try:
            run_ids = latest_index_run_ids(
                conn,
                index_run_id=index_run_id,
                workspace=workspace,
                repo_key=repo_key,
                run_kind="contract",
            )
        except ValueError:
            return []
        placeholders = _placeholders(list(run_ids))
        sql = f"""
            SELECT id, stable_id, display_name, protocol, service, version,
                   method_or_verb, address
            FROM contract_endpoint
            WHERE index_run_id IN ({placeholders})
        """
        params: list[object] = list(run_ids)
        if query is not None:
            pattern = f"%{query}%"
            sql += " AND (stable_id LIKE ? OR display_name LIKE ? OR address LIKE ?)"
            params.extend([pattern, pattern, pattern])
        sql += " ORDER BY stable_id"

        endpoints: list[ContractEndpointSummary] = []
        for row in conn.execute(sql, params):
            constraint_rows = conn.execute(
                """
                SELECT location, field_path, type_name, required
                FROM contract_schema_constraint
                WHERE endpoint_id = ?
                ORDER BY location, field_path
                """,
                (row["id"],),
            ).fetchall()
            endpoints.append(
                ContractEndpointSummary(
                    stable_id=row["stable_id"],
                    display_name=row["display_name"],
                    protocol=row["protocol"],
                    service=row["service"],
                    version=row["version"],
                    method_or_verb=row["method_or_verb"],
                    address=row["address"],
                    schema_constraints=tuple(
                        ContractSchemaConstraintSummary(
                            location=constraint["location"],
                            field_path=constraint["field_path"],
                            type_name=constraint["type_name"],
                            required=(
                                None
                                if constraint["required"] is None
                                else bool(constraint["required"])
                            ),
                        )
                        for constraint in constraint_rows
                    ),
                )
            )
        return endpoints
    finally:
        conn.close()
