-- Upgrade schema v1 → v2 (idempotent where possible)

ALTER TABLE scip_symbol ADD COLUMN relative_path TEXT;
CREATE INDEX IF NOT EXISTS idx_scip_symbol_path ON scip_symbol (index_run_id, relative_path);
ALTER TABLE index_run ADD COLUMN mode TEXT NOT NULL DEFAULT 'snapshot';
ALTER TABLE index_run ADD COLUMN merge_count INTEGER NOT NULL DEFAULT 0;
DELETE FROM meta_schema_version;
INSERT INTO meta_schema_version (version) VALUES (2);
