# The Backend

This backend is built with FastAPI and UV

# Getting Started

1. Make sure to set up [Supabase locally](https://supabase.com/docs/guides/local-development?queryGroups=package-manager&package-manager=brew)
2. Make sure to set up [direnv](https://direnv.net/)
3. cd to the backend directory
4. Copy `.env.example` to `.env` and fill in values
5. Install UV (`make install-uv`)
6. Verify you're running python 3.12 (`python --version`)
7. If not, you can run `uv python install 3.12`
8. Run `make install` to install dependencies
9. Run `make dev` to start the development server

Note: `ENV` is required (set `ENV=dev` for local development or `ENV=staging` for staging, or `ENV=prod` for production).

## Optional: Infisical-managed secrets

By default `make dev` reads from `.env`. To pull secrets from Infisical instead:

1. Install [infisical](https://infisical.com/docs/cli/overview)
2. Run `infisical login`
3. Run `infisical init` (select the correct project)
4. Run `make dev USE_INFISICAL=1`

# Why Makefile?

Python unfortunately lacks the custom script functionality provided by package managers like npm or pnpm. The next best thing we have is a Makefile.
It works the same way as npm scripts, but for any language.

# What is direnv?

Direnv is a tool that lets you execute scripts when you cd into a directory. In this case, we use it to ensure that your python virtual environment is activated when you cd into the backend directory. It's a small QOL devex improvement.

# Other

Service-to-service auth: send `X-API-Key` with your `BACKEND_SECRET` (e.g. from Postman). User auth: send `Authorization: Bearer <Supabase JWT>`.

If ruff is detected as malware on your PC
run this
cd backend
xattr -dr com.apple.quarantine ~/.cache/pre-commit
pre-commit clean
pre-commit install
pre-commit run --all-files
