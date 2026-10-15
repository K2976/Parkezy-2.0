#!/usr/bin/env bash
# Start the API in a production-like shape for load testing: several workers, no --reload,
# no access log, metrics shared across workers. Uses its own database (created on first run).
#
#   ./loadtest/run_api.sh            # foreground; Ctrl+C to stop
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$HERE/../backend"

set -a; source "$HERE/loadtest.env"; set +a

# Isolated Postgres + Redis for load tests (never the dev stack).
DB_NAME="${DATABASE_URL##*/}"
docker compose -f "$HERE/docker-compose.yml" up -d --wait lt-db lt-redis >/dev/null

# prometheus_client multiprocess mode: every worker writes here, /metrics sums them up.
export PROMETHEUS_MULTIPROC_DIR="${TMPDIR:-/tmp}/parkezy-loadtest-metrics"
rm -rf "$PROMETHEUS_MULTIPROC_DIR" && mkdir -p "$PROMETHEUS_MULTIPROC_DIR"

cd "$BACKEND"
uv run alembic upgrade head
echo "API under test: http://localhost:$LOADTEST_PORT  (workers: $LOADTEST_WORKERS, db: $DB_NAME)"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$LOADTEST_PORT" \
  --workers "$LOADTEST_WORKERS" --no-access-log --log-level warning
