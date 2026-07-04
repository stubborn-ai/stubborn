-- Upgrade schema v3 -> v4 (contract evidence metadata)

ALTER TABLE index_run ADD COLUMN run_kind TEXT NOT NULL DEFAULT 'code'
    CHECK (run_kind IN ('code', 'contract'));

CREATE INDEX IF NOT EXISTS idx_index_run_kind ON index_run (run_kind);

CREATE TABLE IF NOT EXISTS contract_endpoint (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    index_run_id    INTEGER NOT NULL REFERENCES index_run(id),
    stable_id       TEXT NOT NULL,
    protocol        TEXT NOT NULL,
    service         TEXT,
    version         TEXT,
    method_or_verb  TEXT,
    address         TEXT NOT NULL,
    display_name    TEXT,
    UNIQUE (index_run_id, stable_id)
);

CREATE TABLE IF NOT EXISTS contract_schema_constraint (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id         INTEGER NOT NULL REFERENCES contract_endpoint(id),
    location            TEXT NOT NULL CHECK (
        location IN ('path','query','header','requestBody','responseBody','message')
    ),
    field_path          TEXT NOT NULL,
    type_name           TEXT,
    required            INTEGER
);

CREATE TABLE IF NOT EXISTS contract_binding (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id         INTEGER NOT NULL REFERENCES contract_endpoint(id),
    code_stable_id      TEXT NOT NULL,
    role                TEXT NOT NULL CHECK (role IN ('provider','consumer')),
    evidence            TEXT NOT NULL CHECK (
        evidence IN ('strong','declared','inferred','unknown')
    ),
    source              TEXT,
    UNIQUE (endpoint_id, code_stable_id, role)
);

CREATE INDEX IF NOT EXISTS idx_contract_binding_code
    ON contract_binding (code_stable_id);

CREATE INDEX IF NOT EXISTS idx_contract_binding_endpoint
    ON contract_binding (endpoint_id);

DELETE FROM meta_schema_version;
INSERT INTO meta_schema_version (version) VALUES (4);
