#Requires -Version 5.1
# Host E2E for spring-petclinic (clone upstream + index + context).
$ErrorActionPreference = "Stop"

$ExampleRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ExampleRoot "..\..")
$UpstreamRoot = Join-Path $ExampleRoot "upstream"
$PinFile = Join-Path $ExampleRoot "upstream.pin"

function Read-PinValue([string]$Key) {
    $line = Get-Content $PinFile | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) { throw "Missing $Key in upstream.pin" }
    return ($line -split "=", 2)[1].Trim()
}

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

$repo = Read-PinValue "repo"
$commit = Read-PinValue "commit"

Write-Host "== spring-petclinic E2E ==" -ForegroundColor Cyan
Assert-Command git
Assert-Command mvn
Assert-Command scip-java
Assert-Command stubborn

if (-not (Test-Path (Join-Path $UpstreamRoot ".git"))) {
    Write-Host "`n[0/6] Clone upstream..." -ForegroundColor Yellow
    git clone --filter=blob:none --no-checkout $repo $UpstreamRoot
    git -C $UpstreamRoot checkout $commit
} else {
    Write-Host "`n[0/6] Use existing upstream at $UpstreamRoot" -ForegroundColor Yellow
    git -C $UpstreamRoot checkout $commit
}

Set-Location $UpstreamRoot

Write-Host "`n[1/6] Maven compile..." -ForegroundColor Yellow
mvn -q -DskipTests package

Write-Host "`n[2/6] scip-java index..." -ForegroundColor Yellow
if (Test-Path index.scip) { Remove-Item index.scip }
scip-java index --build-tool maven

Write-Host "`n[3/6] stubborn index..." -ForegroundColor Yellow
$metadataDir = Join-Path $ExampleRoot "metadata"
New-Item -ItemType Directory -Force -Path $metadataDir | Out-Null
$dbPath = Join-Path $metadataDir "symbols.db"
stubborn index --scip index.scip --out $dbPath

Write-Host "`n[4/6] index summary..." -ForegroundColor Yellow
stubborn info $dbPath

Write-Host "`n[5/6] VetController context..." -ForegroundColor Yellow
$target = python (Join-Path $RepoRoot "scripts\resolve_symbol.py") $dbPath --display-name VetController
$stubPath = Join-Path $metadataDir "vet-controller.stub.java"
stubborn context $dbPath --target $target --out $stubPath

Write-Host "`n[6/6] metrics + verify..." -ForegroundColor Yellow
stubborn metrics $dbPath --target $target --sources src/main/java
python (Join-Path $RepoRoot "scripts\verify_petclinic_context.py")

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  Upstream : $UpstreamRoot @ $commit"
Write-Host "  SQLite   : $dbPath"
Write-Host "  Stub     : $stubPath"
