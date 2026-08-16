# InsightForge — Production Deployment (single server)

Deploys the existing Docker Compose stack (PostgreSQL, FastAPI backend,
Next.js frontend, Qdrant) on a single server running Docker with Compose
v2. No Kubernetes, no cloud-specific services — simple and reproducible.

## Architecture

```
        browser
          │  :3000 (frontend)       :8000 (API)
          ▼                            │
   ┌──────────────┐        ┌───────────▼───────────┐
   │   frontend   │  HTTP  │        backend        │
   │ (Next.js)    │◄──────►│ (FastAPI + worker)    │
   └──────────────┘        └───────┬────────┬──────┘
                                   │        │
                          ┌────────▼──┐  ┌──▼───────┐
                          │ postgres  │  │  qdrant  │
                          │ (volume)  │  │ (volume) │
                          └───────────┘  └──────────┘
   All services on one compose network; only :3000 and :8000 are published.
```

- Persistent data lives in the named volumes `postgres_data` and
  `qdrant_storage` (survive container recreation).
- `restart: unless-stopped` on every service → containers restart
  automatically after a failure or a server reboot (as long as Docker starts
  on boot).
- Secrets live ONLY in the gitignored `deploy/.env.production` (or the repo
  `.env`); nothing secret is committed.

## Deploy

```bash
# 1. Create the production environment file from the template and fill in
#    REAL strong values (see comments in the template).
cp deploy/.env.production.example deploy/.env.production
#    POSTGRES_PASSWORD / AUTH_JWT_SECRET: openssl rand -base64 32
#    API keys: your real Groq / Tavily / Google keys.

# 2. Build and start the production stack on a dedicated project
#    (fresh named volumes get created with the strong credentials).
docker compose --env-file deploy/.env.production -p insightforge-prod up -d --build

# 3. Apply the existing Alembic migrations to the production PostgreSQL.
docker compose -p insightforge-prod exec backend sh -c "cd /app/backend && alembic upgrade head"

# 4. Verify.
curl -s http://localhost:8000/health          # {"status":"ok"}
# open http://localhost:3000
```

## Operations

```bash
# Status / logs
docker compose -p insightforge-prod ps
docker compose -p insightforge-prod logs -f backend

# Backup / restore the production database (see scripts/backup-postgres.sh)
scripts/backup-postgres.sh

# Stop (keeps data) / stop & remove containers (keeps volumes)
docker compose -p insightforge-prod stop
docker compose -p insightforge-prod down

# Wipe data volumes (destructive — only for a fresh reset)
docker compose -p insightforge-prod down -v
```

## Requirements / notes

- Docker Engine + Compose v2 on the server; `postgres:16-alpine` (pinned).
- The backend must reach PostgreSQL and Qdrant on the internal network —
  no host ports published for those services (backend:8000, frontend:3000
  only).
- HTTPS/domain/CI are explicitly later steps; this deploy uses HTTP on the
  host ports.
