#!/usr/bin/env bash
# Verify Python environment and dependencies for NQTaxi Backend
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
if [ -f "../.venv/bin/python" ]; then
  PYTHON="../.venv/bin/python"
fi

echo "==> Dependency verification"
echo "    Python: $PYTHON"
"$PYTHON" --version
echo

echo "==> pip check"
"$PYTHON" -m pip check

echo
echo "==> Import critical packages"
"$PYTHON" -c "
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
"

echo
echo "==> Django system check"
"$PYTHON" manage.py check

echo
echo "==> Run test suite"
"$PYTHON" manage.py test --verbosity=1

echo
echo "All checks passed."
