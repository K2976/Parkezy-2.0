#!/usr/bin/env bash
# Start the API in a production-like shape for load testing: several workers, no --reload,
# no access log, metrics shared across workers. Uses its own database (created on first run).
#
#   ./loadtest/run_api.sh            # foreground; Ctrl+C to stop
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$HERE/../backend"

set -a; source "$HERE/loadtest.env"; set +a

# Create the throwaway database if needed (the dev stack's Postgres container).
DB_NAME="${DATABASE_URL##*/}"
docker compose -f "$HERE/../docker-compose.yml" exec -T db \
  sh -c "psql -U \"\$POSTGRES_USER\" -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\" | grep -q 1 \
         || psql -U \"\$POSTGRES_USER\" -c 'CREATE DATABASE $DB_NAME'" >/dev/null

# prometheus_client multiprocess mode: every worker writes here, /metrics sums them up.
export PROMETHEUS_MULTIPROC_DIR="${TMPDIR:-/tmp}/parkezy-loadtest-metrics"
rm -rf "$PROMETHEUS_MULTIPROC_DIR" && mkdir -p "$PROMETHEUS_MULTIPROC_DIR"

cd "$BACKEND"
uv run alembic upgrade head
echo "API under test: http://localhost:$LOADTEST_PORT  (workers: $LOADTEST_WORKERS, db: $DB_NAME)"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$LOADTEST_PORT" \
  --workers "$LOADTEST_WORKERS" --no-access-log --log-level warning
