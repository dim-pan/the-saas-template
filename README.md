# The SaaS Template — Production-ready SaaS template

**Stop rebuilding the same SaaS plumbing.** The SaaS Template is an opinionated, batteries-included template for shipping a real multi-tenant SaaS — billing, auth, async jobs, webhooks, and infra — already wired up so you can start building your actual product on day one.

If you find this useful, **drop a star** — it helps a lot.

---

## What you get out of the box

- **Multi-tenant by default** — first-class `organizations` + `memberships` tables with role hierarchy (`owner` > `admin` > `member`) and org-scoped RBAC enforced via FastAPI dependencies. No retrofitting tenancy later.
- **Stripe billing, fully wired** — checkout sessions, customer portal, webhook receiver with signature verification and idempotency tracking, denormalized subscription state per org, Slack notifications on subscription changes.
- **Supabase auth + Postgres** — email/password with PKCE, JWT validation in the backend (Supabase client in dev, JWKS in prod), auto-generated Pydantic types from your DB schema (`make dbgen-local`).
- **Async job processing engine** — backend enqueues to AWS SQS, a Python worker polls, processes, and reports status back. Type-safe `JobMessage` schemas, retries, and a `jobs` table for tracking.
- **Webhook gateway** — separate FastAPI service for inbound webhooks (Stripe + third parties), with a processor-routing pattern so adding a new integration is one class.
- **Object storage + media** — Cloudflare R2 (files), Images (transforms), and Stream (video) integrations ready to go.
- **Service-to-service auth** — clean `X-API-Key` pattern with a `Principal(kind='service' | 'user')` model, dev-only auth bypass for fast local iteration.
- **Modern frontend** — React 19, TanStack Router (type-safe routes), TanStack Query (data fetching), Tailwind v4, Zod schemas, Sentry + Segment hooks.
- **Optional Infisical** — pull secrets from Infisical for dev/staging/prod, or just use `.env`. Your call.
- **Docker Compose** — one command spins up backend + frontend.

## Tech stack

| Layer       | Stack                                                              |
| ----------- | ------------------------------------------------------------------ |
| Frontend    | React 19, Vite, TanStack Router/Query, Tailwind v4, Zod, TypeScript |
| Backend     | FastAPI, UV, Supabase client, Stripe, boto3 (SQS), Python 3.12     |
| Engine      | FastAPI gateway + async SQS worker, Pydantic v2                    |
| Database    | Supabase (Postgres), auto-generated Python types                   |
| Auth        | Supabase Auth (PKCE) + JWT/JWKS                                     |
| Payments    | Stripe (checkout, portal, webhooks)                                 |
| Storage     | Cloudflare R2 / Images / Stream                                     |
| Secrets     | `.env` (default) or Infisical (optional)                            |

## Architecture at a glance

```
   Browser  ──JWT──▶  Backend (FastAPI)  ──SQS──▶  Engine Worker
                          │                            │
                          ▼                            ▼
                       Supabase                External APIs
                       (Postgres)
                          ▲
                          │
   Stripe / 3rd parties ──┴──▶  Engine Gateway (webhooks)
```

## Quick start

```bash
# 1. Start Supabase (from /backend)
cd backend && supabase start

# 2. Backend (reads backend/.env)
make dev                                  # http://localhost:8000

# 3. Frontend (reads frontend/.env)
cd ../frontend && pnpm install && pnpm dev    # http://localhost:5173

# 4. (Optional) Engine — async jobs + webhook gateway
cd ../engine
make dev-gateway                          # http://localhost:8001
make dev-worker                           # SQS worker
```

Copy `.env.example` → `.env` in each service first. That's it.

### Or with Docker Compose

```bash
docker compose up --build
```

## Optional: Infisical-managed secrets

Prefer Infisical over `.env`? Opt in per service:

- Backend: `make dev USE_INFISICAL=1`
- Frontend: `pnpm dev:infisical`
- Engine: `make dev-gateway USE_INFISICAL=1`
- Docker: `--build-arg USE_INFISICAL=1` + real `INFISICAL_*` env vars

Run `infisical login` and `infisical init` first.

## Useful local URLs

| URL                            | What                       |
| ------------------------------ | -------------------------- |
| http://localhost:5173          | Frontend                   |
| http://localhost:8000/docs     | Backend API (Swagger)      |
| http://localhost:8001          | Engine webhook gateway     |
| http://localhost:54323         | Supabase Studio            |
| http://localhost:54324         | Mailpit (local email)      |

## Conventions

- **DB tables are plural** (`users`, not `user` — reserved keyword). Child tables prefix the parent: `user_brand`, etc.
- **Service-to-service auth**: `X-API-Key: <BACKEND_SECRET>`
- **User auth**: `Authorization: Bearer <Supabase JWT>`
- **Soft deletes** via an `archived` flag.
- **Org-scoped queries** filter by `organization_id`.

## Supabase

```bash
supabase migration new <NAME>     # create migration
supabase migration up              # apply pending
make dbgen-local                   # regenerate Python DB types
```

If you change Supabase email templates locally:

```bash
supabase stop && supabase start && docker restart supabase_auth_backend
```

## Project layout

```
backend/    FastAPI service — API routes, auth, DB handlers, Stripe, Cloudflare
frontend/   React SPA — TanStack Router pages, Supabase auth, Tailwind UI
engine/     Async worker (SQS) + webhook gateway (FastAPI)
diagrams/   Architecture diagrams
```

Each service has its own README with deeper docs.

## Star history

If The SaaS Template saved you weeks of plumbing, **a star goes a long way**. Issues and PRs welcome.

## License

MIT
