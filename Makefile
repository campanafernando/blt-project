.PHONY: env setup venv install migrate seed api worker web test cov lint schema check up up-full gitea issues down logs ps clean

env:
	@test -f .env || cp .env.example .env
	@echo "Local environment ready. For Compose, review POSTGRES_PASSWORD and S3_SECRET_KEY."

venv:
	@test -d api/.venv || uv venv api/.venv --python 3.12

install: venv
	uv pip install --python api/.venv/bin/python -r api/requirements-dev.txt
	cd web && npm install

migrate:
	api/.venv/bin/python api/manage.py migrate --noinput

seed: migrate
	api/.venv/bin/python api/manage.py seed_demo

setup: env install seed
	@echo "Setup complete. Login: demo / demo12345"

api: env
	api/.venv/bin/python api/manage.py runserver 0.0.0.0:8000

worker: env
	cd api && ../api/.venv/bin/celery -A config worker -l info

web:
	cd web && npm run dev

test:
	cd api && .venv/bin/python -m pytest

cov:
	cd api && .venv/bin/python -m pytest --cov-report=html

lint:
	api/.venv/bin/ruff check api
	cd web && npm run typecheck

schema:
	api/.venv/bin/python api/manage.py spectacular --file api/schema.yaml --validate --fail-on-warn

check: lint test schema
	cd web && npm run build

up: env
	docker compose up -d --build

up-full: env
	docker compose --profile storage up -d --build

gitea: env
	docker compose up -d gitea gitea-init gitea-seed

issues:
	@echo "Gitea issues: http://localhost:3000/blt/tasks/issues"

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

clean:
	rm -rf api/.venv web/node_modules web/dist api/db.sqlite3 api/staticfiles api/media .pytest_cache api/.pytest_cache api/.ruff_cache
