#Requires -Version 5.1
# Smoke-test MCP tools against demo-spring (same calls Cursor agents make).
$ErrorActionPreference = "Stop"

$DemoRoot = Split-Path -Parent $PSScriptRoot
$DbPath = Join-Path $DemoRoot "metadata\symbols.db"
$Sources = Join-Path $DemoRoot "src\main\java"

if (-not (Test-Path $DbPath)) {
    Write-Host "symbols.db missing — run scripts/run-e2e.ps1 first (or: stubborn index --scip index.scip --out metadata/symbols.db)" -ForegroundColor Red
    exit 1
}

$env:STUBBORN_DB = $DbPath

python -c @"
from stubborn.mcp_server.server import get_context, list_symbols, metrics

listing = list_symbols(query='OrderService', limit=3)
print('list_symbols:', listing['returned'], 'hit(s)')
target = listing['symbols'][0]['stable_id']
print('target:', target)

ctx = get_context(target)
print('get_context:', ctx['symbol_count'], 'symbols, ~', ctx['estimated_tokens'], 'tokens')
print('--- stub preview ---')
print(ctx['text'][:600])

kpi = metrics(target, r'$Sources')
print('--- metrics ---')
print('compression_ratio:', kpi['compression_ratio'])
print('token_savings_percent:', kpi['token_savings_percent'])
"@

Write-Host "`nMCP smoke OK. In Cursor: open stubborn repo root, enable MCP server 'stubborn'." -ForegroundColor Green
