#!/usr/bin/env bash
# One-time local setup for NQTaxi Backend (macOS / Linux / WSL)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> NQTaxi Backend setup"
echo "    Directory: $ROOT_DIR"

# Python version check
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.11+ and retry."
  exit 1
fi

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "==> Using Python $PY_VERSION"

# Virtual environment (repo root or local)
VENV_DIR="${VENV_DIR:-$ROOT_DIR/../.venv}"
if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtual environment at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

# Environment file
if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    Edit .env with your DB and Razorpay credentials before running the server."
else
  echo "==> .env already exists (skipped)"
fi

# PostgreSQL via Docker (optional)
if command -v docker >/dev/null 2>&1; then
  echo "==> Starting PostgreSQL (docker compose)"
  docker compose up -d
  echo "    Waiting for database..."
  sleep 3
else
  echo "==> Docker not found — ensure PostgreSQL is running and .env DB_* values are correct."
fi

echo "==> Running migrations"
python manage.py migrate

echo ""
echo "Setup complete."
echo "  Activate venv:  source $VENV_DIR/bin/activate"
echo "  Run server:     python manage.py runserver"
echo "  API docs:       http://127.0.0.1:8000/docs/"
echo "  Run tests:      python manage.py test"
