-- SQLite symbol graph schema v2
-- Adds relative_path (merge), index_run.mode / merge_count

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta_schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO meta_schema_version (version) VALUES (2);

CREATE TABLE IF NOT EXISTS index_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root    TEXT,
    scip_source     TEXT NOT NULL,
    scip_hash       TEXT,
    language        TEXT,
    indexed_at      TEXT NOT NULL DEFAULT (datetime('now')),
    tool_version    TEXT NOT NULL,
    mode            TEXT NOT NULL DEFAULT 'snapshot',
    merge_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scip_symbol (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    stable_id       TEXT NOT NULL,
    display_name    TEXT,
    kind            TEXT,
    signature       TEXT,
    documentation   TEXT,
    relative_path   TEXT,
    UNIQUE (index_run_id, stable_id)
);

CREATE INDEX IF NOT EXISTS idx_scip_symbol_run ON scip_symbol (index_run_id);
CREATE INDEX IF NOT EXISTS idx_scip_symbol_stable ON scip_symbol (stable_id);
CREATE INDEX IF NOT EXISTS idx_scip_symbol_path ON scip_symbol (index_run_id, relative_path);

CREATE TABLE IF NOT EXISTS scip_edge (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    from_symbol_id  INTEGER NOT NULL REFERENCES scip_symbol(id),
    to_symbol_id    INTEGER NOT NULL REFERENCES scip_symbol(id),
    edge_kind       TEXT NOT NULL CHECK (
        edge_kind IN (
            'reference',
            'type',
            'implementation',
            'definition',
            'signature-ref'
        )
    ),
    UNIQUE (index_run_id, from_symbol_id, to_symbol_id, edge_kind)
);

CREATE INDEX IF NOT EXISTS idx_scip_edge_from ON scip_edge (from_symbol_id);
CREATE INDEX IF NOT EXISTS idx_scip_edge_to ON scip_edge (to_symbol_id);
CREATE INDEX IF NOT EXISTS idx_scip_edge_run ON scip_edge (index_run_id);
