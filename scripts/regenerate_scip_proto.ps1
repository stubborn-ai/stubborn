# Regenerate Python bindings after updating proto/scip.proto
# Requires: protoc (libprotoc 3.19+)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ProtoDir = Join-Path $Root "proto"
$OutDir = Join-Path $Root "src\stubborn\ingest\scip_proto"

protoc `
  --python_out=$OutDir `
  --proto_path=$ProtoDir `
  (Join-Path $ProtoDir "scip.proto")

Write-Host "Generated scip_pb2.py in $OutDir"
