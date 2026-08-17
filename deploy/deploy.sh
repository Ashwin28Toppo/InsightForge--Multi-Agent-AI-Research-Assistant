#!/usr/bin/env bash
# ── Production deploy script (Phase 2F Step 16) ─────────────────────────────
# Runs ON the production server. Called by the CD workflow over SSH; also
# runnable locally for validation.
#
# Flow: checkout requested commit -> docker compose build -> up -d (volumes
# preserved, NEVER `down -v`) -> alembic upgrade head -> health checks ->
# record deployed commit.
#
# Environment:
#   DEPLOY_COMMIT  commit/ref to deploy (default: origin/v2-fullstack)
#   DOMAIN         public domain for health checks (default: localhost)
#   CURL_INSECURE  set to 1 to skip TLS verification (local/internal-CA tests)
#   SKIP_GIT       set to 1 to skip git fetch/checkout (local validation on an
#                  already-correct tree)
set -euo pipefail

PROJECT="insightforge-prod"
ENV_FILE="deploy/.env.production"
DOMAIN="${DOMAIN:-localhost}"
CURL_OPTS=(-fsS)
[ "${CURL_INSECURE:-0}" = "1" ] && CURL_OPTS+=(-k)

# Repo root (this file lives in deploy/).
cd "$(dirname "$0")/.."

PREV="$(git rev-parse --short HEAD 2>/dev/null || echo none)"

if [ "${SKIP_GIT:-0}" != "1" ]; then
  echo "==> Fetching and checking out requested commit"
  git fetch origin v2-fullstack --tags
  git checkout "${DEPLOY_COMMIT:-origin/v2-fullstack}"
else
  echo "==> SKIP_GIT=1 — keeping current checkout ($PREV)"
fi

echo "==> Building production images (backend + frontend)"
docker compose --env-file "$ENV_FILE" -p "$PROJECT" build backend frontend

echo "==> Starting / recreating services (volumes preserved — never down -v)"
docker compose --env-file "$ENV_FILE" -p "$PROJECT" up -d

echo "==> Applying Alembic migrations (idempotent)"
docker compose -p "$PROJECT" exec -T backend sh -c "cd /app/backend && alembic upgrade head"

echo "==> Health checks"
ok=""
for _ in 1 2 3 4 5 6; do
  if curl "${CURL_OPTS[@]}" "https://${DOMAIN}/health" 2>/dev/null | grep -q '"status":"ok"'; then
    ok=1
    break
  fi
  sleep 5
done
if [ "${ok:-0}" != "1" ]; then
  echo "ERROR: backend /health did not return ok" >&2
  exit 1
fi
curl "${CURL_OPTS[@]}" -o /dev/null "https://${DOMAIN}/" || {
  echo "ERROR: frontend did not respond" >&2
  exit 1
}
echo "Backend /health OK; frontend OK."

NEW="$(git rev-parse --short HEAD)"
mkdir -p deploy
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) deployed $NEW (previous: $PREV)" >> deploy/deployments.log
echo "==> Deployed $NEW (previous: $PREV)"
