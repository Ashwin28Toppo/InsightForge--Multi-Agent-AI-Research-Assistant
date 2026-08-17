# InsightForge — Production Deployment (single server)

Deploys the existing Docker Compose stack (Caddy, PostgreSQL, FastAPI backend,
Next.js frontend, Qdrant) on a single server running Docker with Compose v2.
No Kubernetes, no cloud-specific services — simple and reproducible.

## Architecture

```
        browser
          │  :80  (HTTP → HTTPS redirect)   :443 (HTTPS)
          ▼
   ┌──────────────┐   Caddy reverse proxy / TLS termination
   │    caddy     │   /auth/*  /research/*  /health  → backend
   └──┬───────┬───┘   everything else                 → frontend
      │       │
      ▼       ▼
   ┌──────────────┐        ┌───────────┐
   │   frontend   │        │  backend  │
   │ (Next.js)    │        │ (FastAPI) │
   └──────────────┘        └─────┬─────┘
                                 │
                        ┌────────▼──┐  ┌──▼───────┐
                        │ postgres  │  │  qdrant  │
                        │ (volume)  │  │ (volume) │
                        └───────────┘  └──────────┘
   All services on one internal network. ONLY :80/:443 are published to the
   host; backend/frontend/PostgreSQL/Qdrant are internal-only.
```

- Persistent data: named volumes `postgres_data`, `qdrant_storage`,
  `caddy_data` (certificates + ACME state) and `caddy_config`.
- `restart: unless-stopped` on every service → containers restart after a
  failure or a server reboot (as long as Docker starts on boot).
- Secrets live ONLY in the gitignored `deploy/.env.production` (or `.env`);
  certificates and private keys live in the `caddy_data` volume — never in
  Git.

## Domain & DNS requirement

1. Buy/own a domain and create a DNS **A record** pointing it at this
   server's **public IP** (e.g. `app.example.com → 203.0.113.10`).
2. Ensure the server's firewall allows inbound **TCP 80** and **TCP 443**
   (Let's Encrypt validates via HTTP-01 on port 80).
3. Set `DOMAIN` (and the URLs below) to that domain in
   `deploy/.env.production`.

> Without a public domain (e.g. `DOMAIN=localhost`), Caddy uses its internal
> CA — HTTPS works locally but is NOT trusted by browsers.

## HTTPS & certificate renewal

- **Caddy** terminates TLS and obtains a **trusted Let's Encrypt certificate
  automatically** for `DOMAIN` (ACME HTTP-01 via the published port 80).
- **Renewal is automatic**: Caddy renews certificates ~30 days before expiry
  and persists ACME state in the `caddy_data` volume, so renewals survive
  container restarts.
- `deploy/Caddyfile` routes `/auth/*`, `/research/*`, `/health` → backend and
  everything else → frontend; HTTP on :80 redirects to HTTPS automatically.
- No certificates/private keys are ever committed — they live in the volume.

## Deploy

```bash
# 1. Create the production environment file from the template and fill in
#    REAL strong values (see comments in the template).
cp deploy/.env.production.example deploy/.env.production
#    POSTGRES_PASSWORD / AUTH_JWT_SECRET: openssl rand -base64 32
#    API keys: your real Groq / Tavily / Google keys.
#    DOMAIN / NEXT_PUBLIC_API_BASE_URL / CORS_ORIGINS: your public domain
#    (AUTH_COOKIE_SECURE=true is already set for HTTPS).

# 2. Build and start the production stack on a dedicated project
#    (fresh named volumes get created with the strong credentials).
docker compose --env-file deploy/.env.production -p insightforge-prod up -d --build

# 3. Apply the existing Alembic migrations to the production PostgreSQL.
docker compose -p insightforge-prod exec backend sh -c "cd /app/backend && alembic upgrade head"

# 4. Verify.
curl -s https://DOMAIN/health          # {"status":"ok"}
curl -sI http://DOMAIN/health          # 308 -> https://DOMAIN/health
# open https://DOMAIN
```

## Operations

```bash
# Status / logs
docker compose -p insightforge-prod ps
docker compose -p insightforge-prod logs -f caddy
docker compose -p insightforge-prod logs -f backend

# Restart the whole stack (after server reboot / config change)
# ALWAYS use the production env file.
docker compose --env-file deploy/.env.production -p insightforge-prod restart
docker compose --env-file deploy/.env.production -p insightforge-prod up -d

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
- A real public domain + DNS A record + open ports 80/443 are required for a
  trusted Let's Encrypt certificate. Until then, `DOMAIN=localhost` gives
  HTTPS with an internal (untrusted) certificate for local verification.
- PostgreSQL and Qdrant are internal-only and never published to the host.
- CI/CD, monitoring, and automated deployments are explicitly later steps.

