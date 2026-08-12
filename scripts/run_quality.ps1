# Calidad local: pytest + coverage (+ Doxygen si está instalado)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Tests unitarios + cobertura (gateway)" -ForegroundColor Cyan
Set-Location "$Root\gateway"
uv sync --group dev | Out-Null
$env:PYTHONPATH = (Get-Location).Path

uv run pytest -q tests/unit -m unit --confcutdir=tests/unit `
  --cov=services.geo_polygon `
  --cov=services.evaluation_metrics `
  --cov=services.farmer_context_service `
  --cov-report=term-missing `
  --cov-report=xml:coverage.xml `
  --cov-report=html:htmlcov `
  --cov-fail-under=40

Write-Host "`nInforme HTML: $Root\gateway\htmlcov\index.html" -ForegroundColor Green
Write-Host "XML Coveralls: $Root\gateway\coverage.xml" -ForegroundColor Green

Set-Location $Root
$doxygen = Get-Command doxygen -ErrorAction SilentlyContinue
if ($doxygen) {
  Write-Host "`n==> Doxygen" -ForegroundColor Cyan
  doxygen Doxyfile
  Write-Host "Docs: $Root\docs\doxygen\html\index.html" -ForegroundColor Green
} else {
  Write-Host "`n[aviso] doxygen no está en PATH. Instálalo para generar docs/doxygen/html" -ForegroundColor Yellow
  Write-Host "  winget install DimitriVanHeesch.Doxygen" -ForegroundColor Yellow
}
