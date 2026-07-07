.PHONY: help install setup migrate run test docker-up docker-down superuser schema clean

PYTHON ?= python
MANAGE = $(PYTHON) manage.py

help:
	@echo "NQTaxi Backend — common commands"
	@echo "  make install     Install Python dependencies"
	@echo "  make setup       Copy .env.example, start DB, migrate"
	@echo "  make migrate     Apply database migrations"
	@echo "  make run         Start development server"
	@echo "  make test        Run test suite"
	@echo "  make docker-up   Start PostgreSQL container"
	@echo "  make docker-down Stop PostgreSQL container"
	@echo "  make superuser   Create Django admin user"
	@echo "  make schema      Export OpenAPI schema to schema.json"

install:
	$(PYTHON) -m pip install --upgrade pip
	pip install -r requirements.txt

setup:
	@test -f .env || cp .env.example .env
	docker compose up -d
	$(MAKE) migrate

migrate:
	$(MANAGE) migrate

run:
	$(MANAGE) runserver

test:
	$(MANAGE) test

docker-up:
	docker compose up -d

docker-down:
	docker compose down

superuser:
	$(MANAGE) createsuperuser

schema:
	$(MANAGE) spectacular --color --file schema.json

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
