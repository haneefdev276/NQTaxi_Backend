# One-time local setup for NQTaxi Backend (Windows PowerShell)
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RootDir

Write-Host "==> NQTaxi Backend setup" -ForegroundColor Cyan
Write-Host "    Directory: $RootDir"

# Python check
$Python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { $null }
if (-not $Python) {
    Write-Host "ERROR: Python not found. Install Python 3.11+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

$PyVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "==> Using Python $PyVersion"

# Virtual environment at repo root
$VenvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path (Split-Path -Parent $RootDir) ".venv" }
if (-not (Test-Path $VenvDir)) {
    Write-Host "==> Creating virtual environment at $VenvDir"
    & $Python -m venv $VenvDir
}

$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
. $Activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Environment file
if (-not (Test-Path ".env")) {
    Write-Host "==> Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
    Write-Host "    Edit .env with your DB and Razorpay credentials before running the server."
} else {
    Write-Host "==> .env already exists (skipped)"
}

# PostgreSQL via Docker (optional)
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "==> Starting PostgreSQL (docker compose)"
    docker compose up -d
    Start-Sleep -Seconds 3
} else {
    Write-Host "==> Docker not found — ensure PostgreSQL is running and .env DB_* values are correct."
}

Write-Host "==> Running migrations"
python manage.py migrate

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "  Activate venv:  $Activate"
Write-Host "  Run server:     python manage.py runserver"
Write-Host "  API docs:       http://127.0.0.1:8000/docs/"
Write-Host "  Run tests:      python manage.py test"
