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

### Status & health

```bash
# Container status (shows per-service health, e.g. (healthy))
docker compose -p insightforge-prod ps

# One-shot health check across the whole stack: services, /health, frontend,
# PostgreSQL, Qdrant, volumes, disk space, and backup recency.
scripts/health-check.sh

# Backend readiness endpoint (behind Caddy):
curl -s https://DOMAIN/health          # {"status":"ok"}
```

### Logs

```bash
docker compose -p insightforge-prod logs -f backend    # app + request logs
docker compose -p insightforge-prod logs -f caddy      # TLS / routing
docker compose -p insightforge-prod logs --tail=200 postgres
docker compose -p insightforge-prod logs --tail=100 qdrant
```

The backend logs structured key=value events (job created/started/completed/
failed, auth success/failure, unexpected exceptions) plus one line per request
(method, path, status, duration, request id, job id). **Sensitive data is
never logged** — passwords, JWTs, API keys, cookies, auth headers, and DB
credentials are excluded by design. Use `docker compose ... logs backend |
grep -v <value>` if you ever need to prove a value is absent.

### Service health (what the healthchecks check)

| Service  | Check | Interval |
|----------|-------|----------|
| postgres | `pg_isready` | 5s |
| qdrant   | HTTP `GET /healthz` on :6333 | 10s |
| backend  | HTTP `GET /health` on :8000 | 15s |
| frontend | HTTP `GET /` on :3000 | 15s |
| caddy    | `wget https://localhost/health` | 15s |

`depends_on` uses `service_healthy`, so startup order is enforced and
`docker compose ps` shows `(healthy)` only when a check passes.

### Checking PostgreSQL

```bash
docker compose -p insightforge-prod exec postgres pg_isready
docker compose -p insightforge-prod exec postgres psql -U insightforge -d insightforge -c '\dt'
```

### Checking Qdrant

```bash
docker compose -p insightforge-prod exec backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://qdrant:6333/healthz', timeout=5).read().decode())"
```

### Backup & restore (PostgreSQL)

```bash
scripts/backup-postgres.sh        # pg_dump -> deploy/backups/insightforge-<ts>.sql
scripts/restore-postgres.sh       # restore (destructive) from the newest dump
```

Backups are written to `deploy/backups/` on the server. Copy them off the
server (e.g. to object storage) — a backup on the same disk is not a disaster
recovery backup. `scripts/health-check.sh` warns when the newest backup is
older than 48h (`MIN_BACKUP_AGE_H`).

### Restarting services

```bash
# After a server reboot or config change — ALWAYS use the production env file.
docker compose --env-file deploy/.env.production -p insightforge-prod restart
docker compose --env-file deploy/.env.production -p insightforge-prod up -d
```

### Disk usage & storage

Persistent data lives in named volumes (`postgres_data`, `qdrant_storage`,
`caddy_data`, `caddy_config`). Check free space and per-volume usage:

```bash
df -h
docker system df                  # total image/container/volume usage
docker system df -v               # per-volume size breakdown
```

Qdrant index and DB growth are the two things to watch. Keep at least a few
GB free; the health-check script fails when free space drops below
`MIN_DISK_GB` (default 5).

### Rollback

The stack is deployed from Git, so rollback = deploy an older commit (volumes
are preserved, so data is untouched):

```bash
DEPLOY_COMMIT=<previous-good-sha> ./deploy/deploy.sh
# or, keeping the current checkout:
SKIP_GIT=1 ./deploy/deploy.sh
```

### Deployment log & failure handling

Every deploy attempt is appended to `deploy/deployments.log`, one line per
attempt, with a status:

```
2025-01-01T00:00:00Z OK commit=92bc944 previous=91abc00
2025-01-01T01:00:00Z FAILED commit=93def01 previous=92bc944
```

- **Success**: `OK` plus the deployed commit and the previous commit.
- **Failure**: `FAILED` is recorded via an `ERR` trap, so a failed build,
  unavailable PostgreSQL/Qdrant, or a failed health check is never silent.
- After a failed deploy, the previous images/containers are left in place
  (the failed run stops before `up -d` succeeds and is recreated), so the app
  keeps serving the last good build; check `docker compose -p insightforge-prod ps`
  and the deploy log, then re-run `deploy/deploy.sh` or roll back.

## Requirements / notes

- Docker Engine + Compose v2 on the server; `postgres:16-alpine` (pinned).
- A real public domain + DNS A record + open ports 80/443 are required for a
  trusted Let's Encrypt certificate. Until then, `DOMAIN=localhost` gives
  HTTPS with an internal (untrusted) certificate for local verification.
- PostgreSQL and Qdrant are internal-only and never published to the host.
- The stack has Docker healthchecks, structured logging, a health-check
  script, and backup scripts; automated CI/CD (GitHub Actions) is set up in
  `.github/workflows/`.

