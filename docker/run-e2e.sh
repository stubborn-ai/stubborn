#!/usr/bin/env bash
# End-to-end: demo-spring -> scip-java -> stubborn context
set -euo pipefail

DEMO_ROOT="${DEMO_ROOT:-/demo}"

cd "${DEMO_ROOT}"

echo "== orders-demo E2E (Docker) =="

echo
echo "[1/5] Maven compile..."
mvn -q -DskipTests package

echo
echo "[2/5] scip-java index..."
rm -f index.scip
scip-java index
test -f index.scip

echo
echo "[3/5] stubborn index..."
mkdir -p metadata
rm -f metadata/symbols.db
stubborn index --scip index.scip --out metadata/symbols.db

echo
echo "[4/5] index summary..."
stubborn info metadata/symbols.db

echo
echo "[5/5] resolve OrderService + emit context..."
target="$(python3 - <<'PY'
import sqlite3
import sys

conn = sqlite3.connect("metadata/symbols.db")
row = conn.execute(
    """
    SELECT stable_id FROM scip_symbol
    WHERE display_name = 'OrderService'
       OR stable_id LIKE '%OrderService#%'
    ORDER BY length(stable_id)
    LIMIT 1
    """
).fetchone()
if not row:
    sys.exit("OrderService symbol not found in index")
print(row[0])
PY
)"

echo "Target: ${target}"
stubborn context metadata/symbols.db \
    --target "${target}" \
    --out metadata/order-service.stub.java

echo
echo "[metrics] compression vs full sources..."
stubborn metrics metadata/symbols.db \
    --target "${target}" \
    --sources src/main/java \
    --stub-out metadata/order-service.stub.java

echo
echo "Done."
echo "  SCIP index : ${DEMO_ROOT}/index.scip"
echo "  SQLite graph: ${DEMO_ROOT}/metadata/symbols.db"
echo "  LLM stub    : ${DEMO_ROOT}/metadata/order-service.stub.java"
