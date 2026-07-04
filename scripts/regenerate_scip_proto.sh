#!/usr/bin/env bash
# Regenerate Python bindings after updating proto/scip.proto
# Requires: protoc (libprotoc 3.19+)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${ROOT}/proto"
OUT_DIR="${ROOT}/src/stubborn/ingest/scip_proto"

if ! command -v protoc >/dev/null 2>&1; then
  echo "Required command not found on PATH: protoc" >&2
  exit 1
fi

protoc \
  --python_out="${OUT_DIR}" \
  --proto_path="${PROTO_DIR}" \
  "${PROTO_DIR}/scip.proto"

echo "Generated scip_pb2.py in ${OUT_DIR}"
