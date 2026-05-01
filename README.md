# The SaaS Template - Production-ready SaaS template

**Stop rebuilding the same SaaS plumbing.** The SaaS Template is an opinionated, batteries-included template for shipping a real multi-tenant SaaS — billing, auth, async jobs, webhooks, and infra — already wired up so you can start building your actual product on day one.

If you find this useful, **drop a star** - it helps a lot.

<img width="450" alt="image" src="https://github.com/user-attachments/assets/6a9a768a-8d71-4f3c-876c-b99f046bdea2" />

**Contributors:** Dimi ([@dim-pan](https://github.com/dim-pan)) · Tinos ([@pTinosq](https://github.com/pTinosq)) · Alex ([@agentf1ash](https://github.com/agentf1ash))

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

| Layer    | Stack                                                               |
| -------- | ------------------------------------------------------------------- |
| Frontend | React 19, Vite, TanStack Router/Query, Tailwind v4, Zod, TypeScript |
| Backend  | FastAPI, UV, Supabase client, Stripe, boto3 (SQS), Python 3.12      |
| Engine   | FastAPI gateway + async SQS worker, Pydantic v2                     |
| Database | Supabase (Postgres), auto-generated Python types                    |
| Auth     | Supabase Auth (PKCE) + JWT/JWKS                                     |
| Payments | Stripe (checkout, portal, webhooks)                                 |
| Storage  | Cloudflare R2 / Images / Stream                                     |
| Secrets  | `.env` (default) or Infisical (optional)                            |

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

Each command below is a long-running process — run each in its own terminal, in this order:

```bash
# 1. Start Supabase (from /backend)
cd backend && supabase start

# 2. Backend (reads backend/.env)
cd backend && make dev                    # http://localhost:8000

# 3. Frontend (reads frontend/.env)
cd frontend && pnpm install && pnpm dev   # http://localhost:5173

# 4. (Optional) Engine — async jobs + webhook gateway
cd engine && make dev-gateway             # http://localhost:8001
cd engine && make dev-worker              # SQS worker (separate terminal)
```

Copy `.env.example` → `.env` in each service first. That's it.

> **First-time setup:** `backend/` and `engine/` ship with a `.envrc` for [direnv](https://direnv.net/). On first run you'll see `direnv: error ... .envrc is blocked`. Approve them once:
>
> ```bash
> cd backend && direnv allow
> cd ../engine && direnv allow
> ```

### One-shot tmux launcher

Prefer not to juggle terminals? `scripts/dev-tmux.sh` spins up the whole stack in a single tmux session (Supabase → backend → frontend → engine gateway + worker), gating the app/engine panes on Supabase being ready:

```bash
./scripts/dev-tmux.sh                       # no ngrok
./scripts/dev-tmux.sh --ngrok <your-url>    # adds an ngrok pane bound to :8000
```

Requires `tmux`. Switch windows with `Ctrl-b n` / `Ctrl-b p`; tear down with `tmux kill-session -t sst`.

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

| URL                        | What                   |
| -------------------------- | ---------------------- |
| http://localhost:5173      | Frontend               |
| http://localhost:8000/docs | Backend API (Swagger)  |
| http://localhost:8001      | Engine webhook gateway |
| http://localhost:54323     | Supabase Studio        |
| http://localhost:54324     | Mailpit (local email)  |

## Conventions

- **DB tables are plural** (`users`, not `user` — reserved keyword). Child tables prefix the parent: `user_brand`, etc.
- **Service-to-service auth**: `X-API-Key: <BACKEND_SECRET>`
- **User auth**: `Authorization: Bearer <Supabase JWT>`
- **Soft deletes** via an `archived` flag.
- **Org-scoped queries** filter by `organization_id`.

## Supabase

```bash
supabase migration new <NAME>     # create migration
make db-migrate                    # apply pending migrations (non-destructive)
make db-reset                      # wipe local DB + replay all migrations (DESTRUCTIVE)
make dbgen-local                   # regenerate Python DB types
```

> **After pulling new migrations:** run `make db-migrate` from `backend/`. `supabase start` alone reuses the existing Docker volume and won't apply new migration files, so without this step you'll see runtime errors like `column ... does not exist`. If your local schema has drifted (manual edits, partial replays), use `make db-reset` instead — it nukes local data and replays every migration from scratch.

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
