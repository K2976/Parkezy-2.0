#!/usr/bin/env bash
# Run a k6 script against the local load-test API and stream results into Prometheus,
# so Grafana shows k6's view (VUs, request rate, p95) next to the server's own metrics.
#
#   ./loadtest/k6.sh search                         # smoke run (2 VUs, 30 s)
#   ./loadtest/k6.sh booking -e PROFILE=stress -e VUS=50
#   ./loadtest/k6.sh race -e RACERS=200
#
# Profiles: smoke | load | stress | spike | soak (-e SOAK_DURATION=2h). VUS sets the peak.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="${1:?usage: k6.sh <search|booking|race|auth> [k6 args...]}"; shift
[ -f "$HERE/data/users.json" ] || { echo "Run the seed first: cd backend && uv run python ../loadtest/seed.py"; exit 1; }
TESTID="${SCRIPT}-$(date +%Y%m%d-%H%M%S)"
echo "k6 run: $TESTID  (filter Grafana by testid=$TESTID)"
exec docker run --rm -i --network host \
  -v "$HERE/k6:/scripts:ro" -v "$HERE/data:/data:ro" \
  -e K6_PROMETHEUS_RW_SERVER_URL="${PROMETHEUS_RW_URL:-http://localhost:9090/api/v1/write}" \
  -e K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),avg,max" \
  -e K6_PROMETHEUS_RW_PUSH_INTERVAL=5s \
  grafana/k6:1.1.0 run -o experimental-prometheus-rw --tag testid="$TESTID" "$@" "/scripts/$SCRIPT.js"
