#!/usr/bin/env bash
# Background worker for the load-test API (delivers outbox events: emails, notifications).
# Run it to see whether the worker keeps up under load (Grafana: "Outbox backlog").
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
set -a; source "$HERE/loadtest.env"; set +a
cd "$HERE/../backend"
exec uv run celery -A app.workers.celery_app worker --loglevel=WARNING --concurrency=4 -n loadtest@%h
