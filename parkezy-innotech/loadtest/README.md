# Load testing (local)

k6 generates the load, Prometheus collects metrics from the API, Postgres, Redis, the host and
k6 itself, and Grafana shows them all on one dashboard. Everything runs on your machine against
a separate `parkezy_loadtest` database, so your dev data is never touched.

```
 k6 (docker) ──requests──▶ API :8001 (4 workers) ──▶ Postgres / Redis
     │                          │ /metrics
     └─remote write─▶ Prometheus :9090 ◀─scrape─ postgres-exporter, redis-exporter, node-exporter
                            │
                       Grafana :3000  (dashboard "Parkezy load test")
```

## Run it

```bash
# 1. Dev stack + monitoring (Prometheus :9090, Grafana :3000, login admin / admin)
docker compose up -d
docker compose --profile monitoring up -d

# 2. The API under test: production-like (no --reload, 4 workers), own database, limits raised
./loadtest/run_api.sh                 # terminal 1
./loadtest/run_worker.sh              # terminal 2 (optional: delivers emails/notifications)

# 3. Test data (500 drivers, 50 hosts, 1000 listings x 4 slots + one single-slot "race" listing)
cd backend && uv run python ../loadtest/seed.py --reset && cd ..

# 4. Load. Open http://localhost:3000 first and watch it live.
./loadtest/k6.sh search                                  # smoke: 2 VUs for 30 s
./loadtest/k6.sh search  -e PROFILE=load   -e VUS=100
./loadtest/k6.sh booking -e PROFILE=stress -e VUS=50
./loadtest/k6.sh booking -e PROFILE=spike  -e VUS=50
./loadtest/k6.sh booking -e PROFILE=soak   -e VUS=30 -e SOAK_DURATION=1h
./loadtest/k6.sh race    -e RACERS=200
./loadtest/k6.sh auth    -e PROFILE=load   -e VUS=20
```

Every run gets a `testid` (printed at the start); pick it in the dashboard's "k6 run" filter to
compare runs. Stop the monitoring stack with `docker compose --profile monitoring down`.

## Scripts

| Script | What it does | Passes when |
|---|---|---|
| `search` | Anonymous map search (sometimes availability-aware), listing detail, reviews | p95: search < 400 ms, detail < 300 ms, reviews < 300 ms |
| `booking` | Signed-in driver: search → detail → quote → book → view → extend quote → cancel (80%) → my bookings | p95 booking < 800 ms, quote/list < 400 ms |
| `race` | N drivers book the same slot and time at the same instant | exactly 1 win, N−1 × 409, 0 errors |
| `auth` | Sign-in throughput (argon2 password hashing is slow by design) | p95 < 1 s |

All scripts also require < 1% unexpected failures and > 99% passed checks. A 409 on a taken
slot is correct behaviour, so it is not counted as a failure (it's graphed as "conflict").

## Profiles (`-e PROFILE=...`, `-e VUS=` sets the peak)

| Profile | Shape | Use it to find |
|---|---|---|
| `smoke` | 2 VUs, 30 s | broken scripts or setup (run first) |
| `load` | ramp to VUS, hold 5 min | normal-day performance |
| `stress` | VUS → 2× → 4× → 6× | where it starts to bend, then break |
| `spike` | sudden jump to 6× for 1 min | recovery after a burst (e.g. a push notification) |
| `soak` | VUS for `SOAK_DURATION` (default 1 h) | leaks, pool exhaustion, slow drift |

## Reading the dashboard

- **p95 latency climbs while requests/s flatten**: you've found the capacity limit. Check which
  row saturates first: CPU (host), connections pinned at 60 (Postgres pool), or lock waits.
- **Postgres connections flat at 60**: the pool is the limit (`LOADTEST_WORKERS` ×
  (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) in `loadtest.env`). Postgres allows 100 by default.
- **Any 5xx**: a bug or overload; the API log in terminal 1 has the traceback.
- **429 above zero**: the raised limits in `loadtest.env` aren't being applied.
- **Outbox backlog growing**: the worker can't keep up (or `run_worker.sh` isn't running).
- **Host CPU near 100%**: k6 runs on the same machine, so numbers are pessimistic. On a deploy,
  run k6 from another machine or Grafana Cloud k6.

## Files

- `loadtest.env`: load-test-only overrides (own DB, raised rate limits, metrics token, 4 workers)
- `run_api.sh`, `run_worker.sh`: start the API / worker with those overrides
- `seed.py`: test data; refuses any database not named `*_loadtest`
- `k6.sh`, `k6/`: runner and scripts (k6 runs in Docker, nothing to install)
- `monitoring/`: Prometheus scrape config, Grafana datasource and dashboard (auto-provisioned)

## Later: cloud

When the API is deployed, point k6 at it with `-e BASE_URL=https://...` and either keep this
Prometheus (`PROMETHEUS_RW_URL=...`) or switch the output to Grafana Cloud k6
(`k6 cloud run --local-execution`). Use a staging deploy with its own database and raised
limits, never production.
