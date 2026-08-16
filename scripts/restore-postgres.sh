#!/usr/bin/env bash
# ── Phase 2F Step 12: PostgreSQL restore (Docker Compose) ────────────────────
# Restores a pg_dump plain-SQL backup into the Compose PostgreSQL database.
# The target database is dropped and recreated first, so this REPLACES the
# current contents of the database.
#
# Usage:
#   scripts/restore-postgres.sh <backup.sql>
#
# Create a backup with: scripts/backup-postgres.sh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup.sql>" >&2
  exit 1
fi
BACKUP="$1"
SERVICE="postgres"
USER="${POSTGRES_USER:-insightforge}"
DB="${POSTGRES_DB:-insightforge}"

if [ ! -f "$BACKUP" ]; then
  echo "Backup file not found: $BACKUP" >&2
  exit 1
fi

echo "Restoring $BACKUP into database '$DB' (user '$USER') ..."
# Terminate connections, drop + recreate the DB, then load the dump.
docker compose exec -T "$SERVICE" psql -U "$USER" -d postgres \
  -c "DROP DATABASE IF EXISTS \"$DB\";" \
  -c "CREATE DATABASE \"$DB\" OWNER \"$USER\";"
docker compose exec -T "$SERVICE" psql -U "$USER" -d "$DB" < "$BACKUP"
echo "Restore complete."
