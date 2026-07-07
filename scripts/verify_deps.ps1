# Verify Python environment and dependencies for NQTaxi Backend
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RootDir

$VenvPython = Join-Path (Split-Path -Parent $RootDir) ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

Write-Host "==> Dependency verification" -ForegroundColor Cyan
Write-Host "    Python: & $VenvPython"

& $VenvPython --version
Write-Host ""

Write-Host "==> pip check" -ForegroundColor Cyan
& $VenvPython -m pip check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> Import critical packages" -ForegroundColor Cyan
& $VenvPython -c @"
import django
import rest_framework
import rest_framework_simplejwt
import corsheaders
import django_filters
import drf_spectacular
import decouple
import razorpay
import psycopg2
import PIL
print('All direct dependencies import successfully.')
print(f'  Django {django.get_version()}')
"@

Write-Host ""
Write-Host "==> Django system check" -ForegroundColor Cyan
& $VenvPython manage.py check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> Run test suite" -ForegroundColor Cyan
& $VenvPython manage.py test --verbosity=1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
