.PHONY: env setup venv install migrate seed api worker web test cov lint schema check up up-full ready gitea issues down logs ps clean

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		for k in $$(sed -n 's/^\([A-Z0-9_]*\)=change-this-.*/\1/p' .env); do \
			sed -i "s|^$$k=.*|$$k=$$(openssl rand -hex 16)|" .env; \
		done; \
		sed -i "s|^SECRET_KEY=django-insecure.*|SECRET_KEY=$$(openssl rand -hex 32)|" .env; \
		echo "Created .env with generated passwords and SECRET_KEY."; \
	else \
		echo ".env already exists; left untouched."; \
	fi

venv:
	@test -d api/.venv || uv venv api/.venv --python 3.12

install: venv
	uv pip install --python api/.venv/bin/python -r api/requirements-dev.txt
	cd web && npm install

migrate:
	api/.venv/bin/python api/manage.py migrate --noinput

seed: migrate
	api/.venv/bin/python api/manage.py seed

setup: env install seed
	@echo "Setup complete. Users: fernando, ballast, lane (password: blt2026)"
	@echo "Without Docker there is no Gitea: use 'make up' for the full stack."

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

# One command: builds, starts everything, waits for the seed (users, tasks, Gitea issues).
up: env
	docker compose up -d --build
	@docker compose wait gitea-seed >/dev/null
	@$(MAKE) --no-print-directory ready

up-full: env
	docker compose --profile storage up -d --build
	@docker compose wait gitea-seed >/dev/null
	@$(MAKE) --no-print-directory ready

ready:
	@echo ""
	@echo "BLT is ready."
	@echo "  App (React)   http://localhost:8080"
	@echo "  HTMX client   http://localhost:8080/app/"
	@echo "  API docs      http://localhost:8000/api/docs/"
	@echo "  Gitea         http://localhost:3000/blt/tasks/issues  (issue #13 is free for a spec)"
	@echo "  Mailpit       http://localhost:8025"
	@echo "  Users         fernando, ballast, lane  (password: blt2026)"
	@grep -q '^OPENCODE_API_KEY=.\+' .env || echo "  AI features   set OPENCODE_API_KEY in .env, then run 'make up' again"

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
