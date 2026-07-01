#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $DemoRoot "..\..")

Set-Location $DemoRoot

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

Write-Host "== orders-demo E2E ==" -ForegroundColor Cyan
Assert-Command mvn
Assert-Command scip-java
Assert-Command stubborn

Write-Host "`n[1/5] Maven compile..." -ForegroundColor Yellow
mvn -q -DskipTests package

Write-Host "`n[2/5] scip-java index..." -ForegroundColor Yellow
if (Test-Path index.scip) { Remove-Item index.scip }
scip-java index
if (-not (Test-Path index.scip)) {
    throw "index.scip was not created"
}

Write-Host "`n[3/5] stubborn index..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path metadata | Out-Null
$dbPath = Join-Path $DemoRoot "metadata\symbols.db"
if (Test-Path $dbPath) { Remove-Item $dbPath }
stubborn index --scip index.scip --out $dbPath

Write-Host "`n[4/5] index summary..." -ForegroundColor Yellow
stubborn info $dbPath

Write-Host "`n[5/5] resolve OrderService + emit context..." -ForegroundColor Yellow
$target = python -c @"
import sqlite3
conn = sqlite3.connect(r'$dbPath')
row = conn.execute(
    '''
    SELECT stable_id FROM scip_symbol
    WHERE display_name = 'OrderService'
       OR stable_id LIKE '%OrderService#'
    ORDER BY length(stable_id)
    LIMIT 1
    '''
).fetchone()
if not row:
    raise SystemExit('OrderService symbol not found in index')
print(row[0])
"@

if (-not $target) {
    throw "Could not resolve OrderService stable_id"
}

Write-Host "Target: $target"
$stubPath = Join-Path $DemoRoot "metadata\order-service.stub.java"
stubborn context $dbPath --target $target --out $stubPath

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  SCIP index : $DemoRoot\index.scip"
Write-Host "  SQLite graph: $dbPath"
Write-Host "  LLM stub    : $stubPath"
Write-Host "`nSee cases/order-service-context.md for expected neighbors."
