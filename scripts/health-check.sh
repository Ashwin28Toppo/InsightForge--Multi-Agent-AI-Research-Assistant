#!/usr/bin/env bash
# ── Production health check (Phase 2F Step 17) ───────────────────────────────
# Run ON the production server (Linux) to verify the whole stack:
#   services up/healthy, backend /health, frontend, PostgreSQL, Qdrant,
#   volumes present, disk space, and backup recency.
#
# Exit code 0 = all checks pass; 1 = at least one check failed.
#
# Environment:
#   DOMAIN            public domain (default: localhost)
#   CURL_INSECURE     set to 1 to skip TLS verification
#   MIN_BACKUP_AGE_H  warn if newest backup older than this (default: 48)
#   MIN_DISK_GB       warn if free disk below this (default: 5)
set -euo pipefail

PROJECT="insightforge-prod"
DOMAIN="${DOMAIN:-localhost}"
MIN_BACKUP_AGE_H="${MIN_BACKUP_AGE_H:-48}"
MIN_DISK_GB="${MIN_DISK_GB:-5}"
CURL_OPTS=(-fsS)
[ "${CURL_INSECURE:-0}" = "1" ] && CURL_OPTS+=(-k)

cd "$(dirname "$0")/.."

failures=0
note() { echo "  [FAIL] $*"; failures=$((failures + 1)); }
pass() { echo "  [ ok ] $*"; }

echo "==> Docker services ($PROJECT)"
docker compose -p "$PROJECT" ps --format 'table {{.Name}}\t{{.Service}}\t{{.Status}}'

for svc in postgres qdrant backend frontend caddy; do
  status="$(docker compose -p "$PROJECT" ps --format '{{.Status}}' "$svc" 2>/dev/null || true)"
  case "$status" in
    *healthy*|*Up*) pass "$svc: $status" ;;
    *) note "$svc: $status (expected 'Up'/'healthy')" ;;
  esac
done

echo "==> Backend /health"
if curl "${CURL_OPTS[@]}" "https://${DOMAIN}/health" 2>/dev/null | grep -q '"status":"ok"'; then
  pass "https://${DOMAIN}/health OK"
else
  note "backend /health did not return ok"
fi

echo "==> Frontend"
if curl "${CURL_OPTS[@]}" -o /dev/null "https://${DOMAIN}/" 2>/dev/null; then
  pass "frontend responded"
else
  note "frontend did not respond"
fi

echo "==> PostgreSQL"
if docker compose -p "$PROJECT" exec -T postgres pg_isready >/dev/null 2>&1; then
  pass "pg_isready OK"
else
  note "PostgreSQL not ready"
fi

echo "==> Qdrant"
if docker compose -p "$PROJECT" exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://qdrant:6333/healthz', timeout=5)" >/dev/null 2>&1; then
  pass "qdrant /healthz OK"
else
  note "Qdrant not reachable"
fi

echo "==> Volumes"
for vol in insightforge-prod_postgres_data insightforge-prod_qdrant_storage insightforge-prod_caddy_data insightforge-prod_caddy_config; do
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    pass "$vol"
  else
    note "$vol missing"
  fi
done

echo "==> Disk space"
free_kb="$(df -Pk . | awk 'NR==2 {print $4}')"
free_gb="$((free_kb / 1024 / 1024))"
if [ "${free_gb:-0}" -ge "$MIN_DISK_GB" ]; then
  pass "${free_gb} GB free"
else
  note "only ${free_gb} GB free (min ${MIN_DISK_GB} GB)"
fi

echo "==> Backups"
newest="$(ls -1t backup/*.sql 2>/dev/null | head -n1 || true)"
if [ -n "$newest" ] && [ -f "$newest" ]; then
  age_s=$(( $(date +%s) - $(stat -c %Y "$newest") ))
  age_h=$(( age_s / 3600 ))
  if [ "$age_h" -le "$MIN_BACKUP_AGE_H" ]; then
    pass "newest backup $newest ($age_h h old)"
  else
    note "newest backup $newest is ${age_h} h old (min ${MIN_BACKUP_AGE_H} h)"
  fi
else
  note "no backup found under backup/"
fi

if [ "$failures" -eq 0 ]; then
  echo "==> ALL CHECKS PASSED"
else
  echo "==> $failures CHECK(S) FAILED"
  exit 1
fi
