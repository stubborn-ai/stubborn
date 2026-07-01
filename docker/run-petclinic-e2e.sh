#!/usr/bin/env bash
# End-to-end: spring-petclinic (upstream clone) -> scip-java -> stubborn
set -euo pipefail

PETCLINIC_ROOT="${PETCLINIC_ROOT:-/petclinic}"
EXAMPLE_ROOT="${EXAMPLE_ROOT:-/opt/stubborn/examples/spring-petclinic}"
PIN_FILE="${EXAMPLE_ROOT}/upstream.pin"
METADATA_DIR="${EXAMPLE_ROOT}/metadata"
TARGET_NAME="${PETCLINIC_TARGET:-VetController}"

repo="$(grep '^repo=' "${PIN_FILE}" | cut -d= -f2- | tr -d '\r')"
commit="$(grep '^commit=' "${PIN_FILE}" | cut -d= -f2- | tr -d '\r')"

echo "== spring-petclinic E2E (Docker) =="
echo "Pin: ${commit}"

if [ ! -d "${PETCLINIC_ROOT}/.git" ]; then
    echo
    echo "[0/6] Clone upstream spring-petclinic..."
    git clone --filter=blob:none --no-checkout "${repo}" "${PETCLINIC_ROOT}"
    git -C "${PETCLINIC_ROOT}" checkout "${commit}"
else
    echo
    echo "[0/6] Upstream already cloned at ${PETCLINIC_ROOT}"
    git -C "${PETCLINIC_ROOT}" checkout "${commit}"
fi

cd "${PETCLINIC_ROOT}"

echo
echo "[1/6] Maven compile..."
mvn -q -DskipTests package

echo
echo "[2/6] scip-java index..."
rm -f index.scip
scip-java index --build-tool maven
test -f index.scip

echo
echo "[3/6] stubborn index..."
mkdir -p "${METADATA_DIR}"
rm -f "${METADATA_DIR}/symbols.db"
stubborn index --scip index.scip --out "${METADATA_DIR}/symbols.db"

echo
echo "[4/6] index summary..."
stubborn info "${METADATA_DIR}/symbols.db"

echo
echo "[5/6] resolve ${TARGET_NAME} + emit context..."
target="$(python3 /opt/stubborn/scripts/resolve_symbol.py \
    "${METADATA_DIR}/symbols.db" \
    --display-name "${TARGET_NAME}")"
echo "Target: ${target}"

stub_path="${METADATA_DIR}/vet-controller.stub.java"
stubborn context "${METADATA_DIR}/symbols.db" \
    --target "${target}" \
    --out "${stub_path}"

echo
echo "[6/6] metrics + verify..."
stubborn metrics "${METADATA_DIR}/symbols.db" \
    --target "${target}" \
    --sources src/main/java \
    --stub-out "${stub_path}"

python3 /opt/stubborn/scripts/verify_petclinic_context.py

echo
echo "Done."
echo "  Upstream   : ${PETCLINIC_ROOT} @ ${commit}"
echo "  SCIP index : ${PETCLINIC_ROOT}/index.scip"
echo "  SQLite graph: ${METADATA_DIR}/symbols.db"
echo "  LLM stub   : ${stub_path}"
