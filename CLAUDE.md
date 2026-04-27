# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

The SaaS Template is a full-stack SaaS platform with a multi-service architecture:

- **Frontend**: React 19 + TypeScript SPA with TanStack Router and TailwindCSS
- **Backend**: Python FastAPI service with Supabase (PostgreSQL) and Stripe integration
- **Engine**: Python service with worker (AWS SQS) and gateway (webhook processor) components
- **Database**: Supabase with auto-generated Python types

All services consume plain env vars and read from a local `.env` by default. **Infisical** is supported as an optional secrets source — opt in with `USE_INFISICAL=1` (Makefiles), `pnpm dev:infisical` (frontend), or `--build-arg USE_INFISICAL=1` (Dockerfiles). The `infisical-auth.sh` entrypoints no-op when Infisical credentials are unset.

## Architecture Patterns

### Service Communication

1. **Frontend → Backend**: HTTP REST API with Supabase JWT authentication
   - Frontend gets access token from Supabase Auth
   - All requests include `Authorization: Bearer <token>` header
   - Backend validates token via Supabase client or JWKS (prod)
   - Response schemas validated with Zod

2. **Backend → Engine**: AWS SQS queue for async task processing
   - Backend enqueues `JobMessage` (JSON) to SQS
   - Engine worker polls SQS, processes task, updates job status via API call
   - Uses `X-API-Key: <BACKEND_SECRET>` for service-to-service auth

3. **External → Backend**: Webhook gateway (engine)
   - Engine gateway (`engine.gateway.main:app` on port 8001) receives webhooks
   - Routes to processor classes based on webhook context (headers, body, etc.)
   - Examples: Stripe webhooks, third-party integrations

### Authentication & Authorization

**Frontend Authentication**:
- Supabase Auth with PKCE flow
- Session stored client-side
- `/login` route handles sign-up/sign-in
- Protected routes via `beforeLoad` guard redirecting to `/login`

**Backend Authorization**:
- Three authentication methods (in order of precedence):
  1. `X-API-Key` header (service-to-service) → `Principal(kind='service')`
  2. Dev auth bypass (dev only): `X-Dev-User-Id` header with `DEV_AUTH_BYPASS_ENABLED=true`
  3. Bearer JWT token → `Principal(kind='user')`
- Role hierarchy: `member < admin < owner` (per-organization)
- `require_org_role(min_role)` dependency enforces org-scoped RBAC

### Database Structure

**Key Tables**:
- `users`: User accounts (created by Supabase Auth)
- `organizations`: Multi-tenant containers
- `memberships`: User ↔ Organization relationship with roles and invitations
- `jobs`: Async task tracking (status: queued/processing/completed/failed)
- `assets`: File uploads with Cloudflare storage metadata
- `subscriptions`: Stripe subscription state per org
- `stripe_webhook_events`: Idempotency tracking for webhooks

**Conventions**:
- Table names plural: `users` not `user` (reserved keyword in SQL)
- Soft deletes via `archived` flag
- Org-scoped queries use `organization_id` filter
- Timestamps: `created_at`, `updated_at`, sometimes `submitted_at`, `finished_at`

## Project Structure

```
backend/
  app/
    api/routes/v1/          # API endpoints (users, orgs, jobs, stripe, assets, memberships)
    auth/                   # JWT verification, Principal/role enforcement
    database/               # Database handlers, auto-generated types (types_autogen.py)
    stripe/                 # Stripe API integration, webhook handling
    clients/                # SQS client for enqueueing jobs
    cloudflare/             # R2 (object storage), Images, Stream integrations
    config.py               # Environment variables
    main.py                 # FastAPI app with CORS middleware
  supabase/
    migrations/             # SQL migration files (ordered by timestamp)
    config.toml             # Supabase local config
  Makefile                  # make dev, make test, make lint, etc.
  pyproject.toml            # UV dependencies, ruff/pyright config

frontend/
  src/
    api/                    # HTTP request helpers (apiGet/apiPost/apiPatch/apiDelete)
    routes/                 # TanStack Router page components and route tree
    components/             # React components (auth, layout, UI)
    hooks/                  # Custom React hooks (useUser, useOrganization, useJobs, useAssets)
    supabase/               # Supabase client setup
  package.json              # pnpm scripts (dev, build, lint, test)
  vite.config.ts            # Build config with TailwindCSS and path alias (@/)

engine/
  src/engine/
    gateway/                # FastAPI app, receives webhooks, routes to processors
    worker/                 # Async job processor, polls SQS, calls processors
    shared/                 # Schemas (JobMessage, TaskStatus), config, API helpers
  Makefile                  # make dev-gateway, make dev-worker, make test, etc.
  pyproject.toml            # Dependencies, ruff/pyright config
```

## Common Development Commands

### Backend (FastAPI)

```bash
cd backend

# Setup
make install                           # Install dependencies (uv sync --locked)
make install-dev                       # Install dev deps + pre-commit hooks
uv python install 3.12                 # Use Python 3.12 (required)

# Development
make dev                               # Start FastAPI dev server (reads .env)
make dev USE_INFISICAL=1               # Same, but pull secrets via `infisical run`
make lint                              # Run ruff + pyright
make lint-fix                          # Auto-fix with ruff, then pyright
make format                            # Format with ruff
make test                              # Run all pytest tests
make test-unit                         # Run unit tests only
make test-integration                  # Run integration tests with durations

# Database
supabase start                          # Start local Supabase (required for backend dev)
supabase stop                           # Stop local Supabase
supabase migration new <NAME>           # Create new migration file
make dbgen-local                        # Regenerate types_autogen.py from local Supabase schema
```

**Environment**:
- Local: `ENV=dev` (set via Infisical or .env)
- Dev auth bypass: Set `DEV_AUTH_BYPASS_ENABLED=true` and `DEV_DEFAULT_USER_ID=<uuid>`
- Service secret: `BACKEND_SECRET` (used by engine for SQS job updates)

### Frontend (Vite + React)

```bash
cd frontend

# Setup
pnpm install                           # Install dependencies
pnpm format                            # Format with Prettier
pnpm lint                              # Run ESLint
pnpm lint:fix                          # Auto-fix linting issues

# Development
pnpm run dev                           # Start Vite dev server on port 5173 (reads .env)
pnpm run dev:infisical                 # Same, but pull secrets via `infisical run`
pnpm run build                         # Build for production
pnpm run preview                       # Preview production build locally

# Testing
pnpm test                              # Run unit tests + e2e tests
pnpm test:unit                         # Run unit tests only (vitest)
pnpm test:e2e                          # Run Playwright e2e tests
```

**Environment**:
- `VITE_BACKEND_URL`: Backend API URL (e.g., `http://localhost:8000`)
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY`: Supabase config
- `VITE_SENTRY_DSN`, `VITE_SEGMENT_WRITE_KEY`: Optional monitoring/analytics

### Engine (Python async worker + gateway)

```bash
cd engine

# Setup
make install                           # Install dependencies
make install-dev                       # Install dev deps + pre-commit hooks

# Development (reads engine/.env by default)
make dev-gateway                       # Start FastAPI gateway (webhook receiver, port 8001)
make dev-worker                        # Start SQS job worker (polls and processes tasks)
make dev-gateway USE_INFISICAL=1       # Same, but require INFISICAL_PROJECT_ID and pull from Infisical
make lint                              # Run ruff + pyright
make test                              # Run pytest tests
```

**Key**: When `USE_INFISICAL=1`, both gateway and worker require `INFISICAL_PROJECT_ID`. Otherwise they only need `engine/.env`.

### Docker Compose

```bash
docker-compose build                   # Build all service images
docker-compose up                      # Start all services (backend:8000, frontend:5173, engine services)
```

## Authentication Flow

### User Sign-Up/Sign-In (Frontend)

1. User submits email/password on `/login`
2. Frontend calls Supabase Auth API (managed by Supabase, not backend)
3. Supabase creates user and returns JWT
4. `authConfirm` route handles confirmation emails
5. JWT stored in browser session (managed by AuthProvider)

### API Request (Frontend → Backend)

1. Frontend calls `apiRequest()` helper
2. Helper fetches access token: `supabase.auth.getSession()`
3. Sets `Authorization: Bearer <token>` header
4. Backend validates token and extracts user_id via `get_principal()`

### Service-to-Service (Engine → Backend)

1. Engine reads `BACKEND_SECRET` from Infisical
2. Sets `X-API-Key: <BACKEND_SECRET>` header
3. Backend endpoint requires `require_engine_secret()` dependency
4. Principal authenticated as `kind='service'`

## Stripe Integration

**Implementation**:
- Webhook listener at `POST /api/v1/stripe/webhook`
- Signature verification via `construct_event()`
- Idempotency: Stripe events stored in `stripe_webhook_events` table
- Handles: checkout completed, subscription events, invoice payments

**Flow**:
1. Customer initiates checkout → Backend creates Stripe session
2. Customer pays → Stripe webhook → Backend webhook endpoint
3. Backend stores event, updates `subscriptions` table
4. Slack notification sent for subscription changes
5. Org denormalized fields updated (`stripe_customer_id`, `current_period_end`, etc.)

## Key Dependencies & Versions

**Backend**:
- `fastapi>=0.125.0`, `uvicorn` (web framework)
- `supabase>=2.27.0` (database client)
- `stripe>=14.3.0` (payments)
- `boto3>=1.42.46` (AWS SQS)
- `ruff`, `pyright` (linting/type checking)
- Python 3.12+

**Frontend**:
- `react@19`, `react-dom@19` (UI)
- `@tanstack/react-router@1.141.4` (routing)
- `@tanstack/react-query@5.90.1` (data fetching)
- `@supabase/supabase-js@2.90.1` (auth/database)
- `tailwindcss@4.1.18` (styling)
- `zod@4.2.1` (schema validation)
- `@sentry/react@10.32.0` (error tracking)
- `@segment/analytics-next@1.81.1` (analytics)
- TypeScript ~5.9.3

**Engine**:
- `fastapi>=0.125.0`, `uvicorn>=0.40.0` (gateway web server)
- `boto3>=1.42.46` (SQS client)
- `pydantic>=2.12.5` (schemas)

## Environment & Secrets Management

**Infisical** is supported but optional for all three services:
- Default: each service reads `.env` directly (no CLI required).
- Opt in via `USE_INFISICAL=1` (backend/engine Makefiles), `pnpm dev:infisical` (frontend), or `--build-arg USE_INFISICAL=1` (Dockerfiles).
- When opting in: `infisical login`, `infisical init`, then run the dev command.

**Local Development (.env files)**:
- Backend: `.env` overrides specific values (use for local testing)
- Frontend: `.env` passed to Vite (same pattern)
- Engine: `.env` for local overrides
- `.env.example` files document required keys

**Docker Environment**:
- `docker-compose.yml` passes Infisical credentials as environment variables
- Containers execute `infisical-auth.sh` wrapper scripts
- Backend: Infisical → FastAPI with UV
- Frontend: Infisical → Vite dev server

## Testing

**Backend**:
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Pytest configuration: `pyproject.toml` with pythonpath, testpaths
- Run specific test: `make test-unit` or `uv run pytest tests/unit/test_file.py`

**Frontend**:
- Unit tests: Vitest (same as Jest)
- E2E tests: Playwright
- Test patterns: Pages and hooks have corresponding `.test.ts(x)` files

**Database**:
- Supabase automatically creates local test DB
- Migrations applied during `supabase start`
- Note: Database types auto-generated via `npx supabase gen types`

## Code Generation

### Database Types
```bash
cd backend
make dbgen-local    # Generates app/database/types_autogen.py from local Supabase
```
This creates Pydantic models for all tables/views, used throughout database handlers.

### Pre-commit Hooks
- Configured in `.pre-commit-config.yaml` (backend/engine)
- Runs: ruff format, ruff lint, pyright
- Install hooks: `make install-dev`

## Deployment Notes

**Production Differences**:
- `ENV=prod` disables dev auth bypass
- JWT validation via JWKS (JSON Web Key Set) instead of Supabase client
- Stripe operates in live mode
- Sentry error tracking enabled
- Secrets from Infisical (prod environment)

**Key Endpoints**:
- Backend: `http://localhost:8000` (dev) or production domain
- Frontend: `http://localhost:5173` (dev) or production domain
- Engine Gateway: `http://localhost:8001` (webhook receiver)
- Engine Worker: Runs in background, polls SQS
- Supabase Studio: `http://localhost:54323/` (local only)
- Mailpit (email testing): `http://localhost:54324/` (local only)

## Important Implementation Details

### Org-Scoped Operations

Most operations are organization-scoped. Pattern:
```python
@router.get('/org/{organization_id}/items')
def list_items(
    organization_id: UUID,
    context: OrgRoleContext = Depends(require_org_role('member'))
):
    # context.org, context.user, context.membership available
    # Query filtered by organization_id
```

### Job Queue Flow

1. Frontend/Backend calls SQS endpoint to enqueue task
2. Backend creates `jobs` row with status='queued'
3. Engine worker polls SQS, validates `JobMessage`
4. Updates job status='processing' via API
5. Processor runs task (e.g., external API call)
6. Job status updated to 'completed' or 'failed'

### Error Handling

- Backend: HTTPException with status codes
- Frontend: `ApiError` with status, body
- Both: Sentry integration for error tracking
- Database: Handlers raise HTTPException on not found

### Database Handlers Pattern

```python
class SomeHandler(DatabaseHandler[PublicSomeTable, PublicSomeTableInsert, PublicSomeTableUpdate]):
    def __init__(self, client: Client, organization_id: UUID | None = None):
        super().__init__(
            client,
            'some_table',
            row_model=PublicSomeTable,
            organization_id=organization_id
        )
```
Provides CRUD methods: `get_item()`, `list_items()`, `insert_item()`, `update_item()`, `delete_item()`.

## Git Workflow

- Single initial commit
- Use feature branches for new work
- Pre-commit hooks run automatically (format, lint, type check)
- No force pushes to main
