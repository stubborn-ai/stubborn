#Requires -Version 5.1
<#
.SYNOPSIS
  Duke's Bank bank module -> scip-java -> anchor-stubborn context (AccountControllerBean).

.DESCRIPTION
  Expects sibling layout:
    .../stubborn-ai/stubborn/examples/dukesbank/  (this script)
    .../dukesbank/src/j2eetutorial14/examples/bank/

.EXAMPLE
  .\scripts\run-e2e.ps1
  .\scripts\run-e2e.ps1 -BankRoot "D:\legacy\dukesbank\src\j2eetutorial14\examples\bank"
#>
param(
    [string]$BankRoot = ""
)

$ErrorActionPreference = "Stop"

$ExampleRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ExampleRoot "..\..")

if (-not $BankRoot) {
    $BankRoot = Join-Path $RepoRoot "..\..\dukesbank\src\j2eetutorial14\examples\bank"
}
if (-not (Test-Path $BankRoot)) {
    throw "Duke's Bank module not found. Clone dukesbank as sibling of anchor-migration or pass -BankRoot."
}

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

Write-Host "== Duke's Bank anchor-stubborn E2E ==" -ForegroundColor Cyan
Write-Host "Bank module: $BankRoot"

Assert-Command mvn
Assert-Command scip-java
Assert-Command anchor-stubborn
Assert-Command python

Push-Location $BankRoot
try {
    Write-Host "`n[1/6] Maven compile..." -ForegroundColor Yellow
    mvn -q -DskipTests package

    Write-Host "`n[2/6] scip-java index..." -ForegroundColor Yellow
    if (Test-Path index.scip) { Remove-Item index.scip }
    scip-java index
    if (-not (Test-Path index.scip)) { throw "index.scip was not created" }

    $dbPath = Join-Path $ExampleRoot "metadata\symbols.db"
    New-Item -ItemType Directory -Force -Path (Split-Path $dbPath) | Out-Null
    if (Test-Path $dbPath) { Remove-Item $dbPath }

    Write-Host "`n[3/6] anchor-stubborn index..." -ForegroundColor Yellow
    anchor-stubborn index --scip index.scip --out $dbPath

    Write-Host "`n[4/6] resolve AccountControllerBean..." -ForegroundColor Yellow
    $target = python (Join-Path $RepoRoot "scripts\resolve_symbol.py") $dbPath --display-name AccountControllerBean
    if (-not $target) { throw "AccountControllerBean symbol not found" }
    Write-Host "Target: $target"

    Write-Host "`n[5/6] emit java-stub + anchor-dsl..." -ForegroundColor Yellow
    $stubPath = Join-Path $ExampleRoot "metadata\account-controller.stub.java"
    $dslPath = Join-Path $ExampleRoot "metadata\account-controller.anchor-dsl"
    anchor-stubborn context $dbPath --target $target --out $stubPath
    anchor-stubborn context $dbPath --target $target --format anchor-dsl `
        --member-signatures neighbors --javadoc summary --out $dslPath

    Write-Host "`n[6/6] metrics..." -ForegroundColor Yellow
    anchor-stubborn metrics $dbPath --target $target --sources src
}
finally {
    Pop-Location
}

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  SQLite graph : $dbPath"
Write-Host "  java-stub    : $stubPath"
Write-Host "  anchor-dsl   : $dslPath"
Write-Host "`nVerify: python scripts/verify_dukesbank_context.py (from repo root)"
