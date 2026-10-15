#!/usr/bin/env bash
# Failure injection: break one dependency at a time while load runs, and record what users see.
#
#   ./loadtest/chaos.sh            # ~9 minutes; run while ./loadtest/k6.sh booking ... is going
#
# Each fault lasts FAULT_SECONDS, then the system gets RECOVER_SECONDS to heal on its own.
# Timestamps are printed so you can line them up with the Grafana dashboard.
# Faults target the ISOLATED load-test stack (loadtest/docker-compose.yml) only; the dev stack and
# the dev API on :8000 are never touched.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="docker compose -f $HERE/docker-compose.yml"
FAULT_SECONDS="${FAULT_SECONDS:-30}"
RECOVER_SECONDS="${RECOVER_SECONDS:-45}"
API="http://localhost:${LOADTEST_PORT:-8001}"
FAULTS=" ${FAULTS:-1 2 3 4 5 6} "  # e.g. FAULTS="2 4" runs only those
# The Celery worker started by run_worker.sh (exact command, so nothing else ever matches).
WORKER_PATTERN="celery -A app.workers.celery_app worker --loglevel=WARNING --concurrency=4 -n loadtest@"
want() { [[ "$FAULTS" == *" $1 "* ]]; }

say() { echo "[$(date +%H:%M:%S)] $*"; }
probe() {  # what a user would see right now: status + time of a few representative calls
  local r1 r2 r3 r4
  r1=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/health/live")
  r2=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/health/ready")
  r3=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/v1/config")
  r4=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/v1/listings?latitude=12.97&longitude=77.59&radius_km=2")
  say "   probe  live=$r1  ready=$r2  config=$r3  search=$r4"
}
during() { for _ in $(seq 1 $((FAULT_SECONDS / 10))); do sleep 10; probe; done; }
recover() { sleep "$RECOVER_SECONDS"; probe; }

say "baseline"; probe

if want 1; then
say "FAULT 1: Redis frozen (cache, rate limiter, Celery broker, QR one-time tokens)"
$COMPOSE pause lt-redis >/dev/null; during; $COMPOSE unpause lt-redis >/dev/null; say "Redis back"; recover
fi

if want 2; then
say "FAULT 2: Postgres frozen"
$COMPOSE pause lt-db >/dev/null; during; $COMPOSE unpause lt-db >/dev/null; say "Postgres back"; recover
fi

if want 3; then
say "FAULT 3: one API worker process killed (SIGKILL)"
# A worker is a process holding the listening socket; never the master (its parent), whose death
# would orphan every worker.
holders=$(ss -ltnp "sport = :${LOADTEST_PORT:-8001}" | grep -oE "pid=[0-9]+" | cut -d= -f2 | sort -u)
victim=""
for p in $holders; do  # a worker's parent (the master) also holds the socket
  echo "$holders" | grep -qx "$(ps -o ppid= -p "$p" | tr -d ' ')" && { victim=$p; break; }
done
if [ -n "${victim:-}" ]; then kill -9 "$victim"; say "killed worker pid $victim"; else say "no worker child found"; fi
during; recover
fi

if want 4; then
say "FAULT 4: bookings table locked by a stuck transaction"
$COMPOSE exec -T lt-db psql -U parkezy -d parkezy_loadtest -c \
  "BEGIN; LOCK TABLE bookings IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep($FAULT_SECONDS); COMMIT;" >/dev/null &
lockpid=$!; during; wait $lockpid; say "lock released"; recover
fi

if want 5; then
say "FAULT 5: Postgres connection slots exhausted by another client"
$COMPOSE exec -T lt-db sh -c "for i in \$(seq 1 85); do psql -U parkezy -d parkezy_loadtest -c 'SELECT pg_sleep($FAULT_SECONDS)' >/dev/null 2>&1 & done; wait" &
hogpid=$!; during; wait $hogpid; say "connections released"; recover
fi

if want 6; then
say "FAULT 6: background worker stopped (emails/notifications stop flowing)"
pkill -STOP -f "$WORKER_PATTERN" && say "worker paused"
during
pkill -CONT -f "$WORKER_PATTERN" && say "worker resumed"; recover
fi

say "done"; probe
