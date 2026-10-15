#!/usr/bin/env bash
# Failure injection: break one dependency at a time while load runs, and record what users see.
#
#   ./loadtest/chaos.sh            # ~9 minutes; run while ./loadtest/k6.sh booking ... is going
#
# Each fault lasts FAULT_SECONDS, then the system gets RECOVER_SECONDS to heal on its own.
# Timestamps are printed so you can line them up with the Grafana dashboard.
# NOTE: Redis/Postgres faults also affect the dev API on :8000 (they share the containers).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
COMPOSE="docker compose -f $HERE/../docker-compose.yml"
FAULT_SECONDS="${FAULT_SECONDS:-30}"
RECOVER_SECONDS="${RECOVER_SECONDS:-45}"
API="http://localhost:${LOADTEST_PORT:-8001}"

say() { echo "[$(date +%H:%M:%S)] $*"; }
probe() {  # what a user would see right now: status + time of a few representative calls
  local r1 r2
  r1=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/v1/config")
  r2=$(curl -s -o /dev/null -m 20 -w "%{http_code}/%{time_total}s" "$API/health/ready")
  say "   probe  config=$r1  ready=$r2"
}
during() { for _ in $(seq 1 $((FAULT_SECONDS / 10))); do sleep 10; probe; done; }
recover() { sleep "$RECOVER_SECONDS"; probe; }

say "baseline"; probe

say "FAULT 1: Redis frozen (cache, rate limiter, Celery broker, QR one-time tokens)"
$COMPOSE pause redis >/dev/null; during; $COMPOSE unpause redis >/dev/null; say "Redis back"; recover

say "FAULT 2: Postgres frozen"
$COMPOSE pause db >/dev/null; during; $COMPOSE unpause db >/dev/null; say "Postgres back"; recover

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

say "FAULT 4: bookings table locked by a stuck transaction"
$COMPOSE exec -T db psql -U parkezy -d parkezy_loadtest -c \
  "BEGIN; LOCK TABLE bookings IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep($FAULT_SECONDS); COMMIT;" >/dev/null &
lockpid=$!; during; wait $lockpid; say "lock released"; recover

say "FAULT 5: Postgres connection slots exhausted by another client"
$COMPOSE exec -T db sh -c "for i in \$(seq 1 85); do psql -U parkezy -d parkezy_loadtest -c 'SELECT pg_sleep($FAULT_SECONDS)' >/dev/null 2>&1 & done; wait" &
hogpid=$!; during; wait $hogpid; say "connections released"; recover

say "FAULT 6: background worker stopped (emails/notifications stop flowing)"
pkill -STOP -f "loadtest@" && say "worker paused"
during
pkill -CONT -f "loadtest@" && say "worker resumed"; recover

say "done"; probe
