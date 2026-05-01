USE_INFISICAL ?= 0
RUN_PREFIX := $(if $(filter 1,$(USE_INFISICAL)),infisical run --,)

dev:
	$(RUN_PREFIX) uv run --env-file=.env fastapi dev app/main.py

format:
	uv run ruff format

lint:
	uv run ruff check app
	uv run pyright

lint-fix:
	uv run ruff check --fix app
	uv run pyright

test:
	uv run pytest

test-unit:
	uv run pytest --durations=30 tests/unit/

test-integration:
	uv run pytest --durations=0 tests/integration/

install-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

install:
	uv sync --locked

install-test:
	uv sync --locked --extras test

install-dev:
	uv sync --locked --all-extras
	uv run pre-commit install
	uv run pre-commit autoupdate

dbgen-local:
	npx supabase gen types --lang=python --local | uv run python ./scripts/postprocess_db_types.py > ./app/database/types_autogen.py
	uv run ruff check --fix ./app/database/types_autogen.py
	uv run ruff format ./app/database/types_autogen.py

# Apply any pending migrations to the running local Supabase DB. Non-destructive.
db-migrate:
	supabase migration up

# Wipe the local Supabase DB and re-run every migration from scratch. DESTRUCTIVE — clears all local data.
db-reset:
	supabase db reset
