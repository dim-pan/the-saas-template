UV_VERSION=0.10.2

-include .env

USE_INFISICAL ?= 0
INFISICAL_SECRET_ENV ?= dev

INFISICAL_PREFIX := $(if $(filter 1,$(USE_INFISICAL)),env -u INFISICAL_TOKEN infisical run --projectId "$(INFISICAL_PROJECT_ID)" --env "$(INFISICAL_SECRET_ENV)" --,)

.PHONY: _require-infisical-project-id
_require-infisical-project-id:
	@if [ "$(USE_INFISICAL)" = "1" ] && [ -z "$(INFISICAL_PROJECT_ID)" ]; then \
		echo "ERROR: USE_INFISICAL=1 but INFISICAL_PROJECT_ID is not set. Set it in your shell or in engine/.env (or export it before running make)."; \
		exit 1; \
	fi

install-uv:
	curl --proto '=https' --tlsv1.2 -LsSf https://github.com/astral-sh/uv/releases/download/$(UV_VERSION)/uv-installer.sh | sh

install:
	uv sync --locked

install-test:
	uv sync --locked --extra test

install-dev:
	uv sync --locked --all-extras
	uv run pre-commit install
	uv run pre-commit autoupdate

lint-check:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run pyright

lint:
	uv run ruff check --fix
	uv run ruff format
	uv run pyright

test:
	ENV=staging uv run pytest --durations=30 tests/unit/

dev-worker:
	@$(MAKE) _require-infisical-project-id
	$(INFISICAL_PREFIX) uv run --env-file=.env python -m engine.worker.main

dev-gateway:
	@$(MAKE) _require-infisical-project-id
	$(INFISICAL_PREFIX) uv run --env-file=.env uvicorn engine.gateway.main:app --host 0.0.0.0 --port 8001 --reload
