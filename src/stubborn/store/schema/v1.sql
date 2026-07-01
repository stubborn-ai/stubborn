-- SQLite symbol graph schema v1
-- SSoT snapshot store for SCIP-derived code symbol indexes

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta_schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO meta_schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS index_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root    TEXT,
    scip_source     TEXT NOT NULL,
    scip_hash       TEXT,
    language        TEXT,
    indexed_at      TEXT NOT NULL DEFAULT (datetime('now')),
    tool_version    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scip_symbol (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    stable_id       TEXT NOT NULL,
    display_name    TEXT,
    kind            TEXT,
    signature       TEXT,
    documentation   TEXT,
    UNIQUE (index_run_id, stable_id)
);

CREATE INDEX IF NOT EXISTS idx_scip_symbol_run ON scip_symbol (index_run_id);
CREATE INDEX IF NOT EXISTS idx_scip_symbol_stable ON scip_symbol (stable_id);

CREATE TABLE IF NOT EXISTS scip_edge (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    from_symbol_id  INTEGER NOT NULL REFERENCES scip_symbol(id),
    to_symbol_id    INTEGER NOT NULL REFERENCES scip_symbol(id),
    edge_kind       TEXT NOT NULL CHECK (
        edge_kind IN ('reference', 'type', 'implementation', 'definition')
    ),
    UNIQUE (index_run_id, from_symbol_id, to_symbol_id, edge_kind)
);

CREATE INDEX IF NOT EXISTS idx_scip_edge_from ON scip_edge (from_symbol_id);
CREATE INDEX IF NOT EXISTS idx_scip_edge_to ON scip_edge (to_symbol_id);
CREATE INDEX IF NOT EXISTS idx_scip_edge_run ON scip_edge (index_run_id);
