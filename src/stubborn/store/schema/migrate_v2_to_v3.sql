-- Upgrade schema v2 -> v3 (workspace/repo metadata)

CREATE TABLE IF NOT EXISTS workspace (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    root            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS repo (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id    INTEGER NOT NULL REFERENCES workspace(id),
    repo_key        TEXT NOT NULL,
    root            TEXT,
    language        TEXT,
    artifact        TEXT,
    priority        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (workspace_id, repo_key)
);

CREATE INDEX IF NOT EXISTS idx_repo_workspace ON repo (workspace_id);
CREATE INDEX IF NOT EXISTS idx_repo_key ON repo (repo_key);

ALTER TABLE index_run ADD COLUMN repo_id INTEGER REFERENCES repo(id);
CREATE INDEX IF NOT EXISTS idx_index_run_repo_latest ON index_run (repo_id, id);
CREATE INDEX IF NOT EXISTS idx_scip_symbol_run_stable ON scip_symbol (index_run_id, stable_id);

DELETE FROM meta_schema_version;
INSERT INTO meta_schema_version (version) VALUES (3);
