#!/usr/bin/env bash
# ── Phase 2F Step 12: PostgreSQL backup (Docker Compose) ─────────────────────
# Dumps the Compose PostgreSQL database to a plain SQL file on the host using
# pg_dump inside the postgres container.
#
# Usage:
#   scripts/backup-postgres.sh [output.sql]
#   (default output: backup/insightforge-YYYYMMDD-HHMMSS.sql)
#
# Restore with: scripts/restore-postgres.sh <backup.sql>
set -euo pipefail

SERVICE="postgres"
USER="${POSTGRES_USER:-insightforge}"
DB="${POSTGRES_DB:-insightforge}"
OUT="${1:-backup/insightforge-$(date +%Y%m%d-%H%M%S).sql}"

mkdir -p "$(dirname "$OUT")"
echo "Backing up database '$DB' (user '$USER') to $OUT ..."
docker compose exec -T "$SERVICE" pg_dump -U "$USER" -d "$DB" > "$OUT"
echo "Backup complete: $OUT"
