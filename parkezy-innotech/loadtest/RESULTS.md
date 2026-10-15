# Load and failure test results — 2026-10-15

Local run: API with 4 workers on a 16-core / 13 GB machine, k6 on the same machine, separate
`parkezy_loadtest` database (500 drivers, 50 hosts, 1000 listings). Numbers are for this machine
and are pessimistic (k6 competes for CPU), but where things break, and how, carries over to a deploy.

## What held up

- **Correctness under load:** 69,424 requests across all 89 routes (621 complete user journeys,
  up to 90 concurrent users): **0 wrong answers, 0 server errors**.
- **Double booking:** 100 drivers booking one slot at the same instant → exactly 1 booked, 99 × 409.
- **Retries:** 20 parallel retries with one Idempotency-Key → 1 booking. 20 parallel sign-ups with
  one email → 1 account, 19 × 409.
- **Bad input:** malformed/huge/deep JSON, NaN/inf/1e308 numbers, dates in year 0001/9999, garbage
  cursors and ids, tampered or `alg=none` JWTs, path traversal → all clean 4xx.
- **Brute force (real limits):** login blocked with 429 after 10 tries, with `Retry-After`.
- **Worker crash:** a killed API worker was respawned in seconds, 0 of 1,957 requests failed.
- **Database:** 0 deadlocks, never more than 6 queries active at once.

## Capacity (peak sustained, this machine, 4 workers)

| Endpoint | req/s | Endpoint | req/s |
|---|---|---|---|
| `GET /v1/config` | 1,634 | `GET /v1/listings/{id}` | 441 |
| `GET /v1/me` | 1,009 | `GET /v1/bookings` | 266 |
| `GET /v1/listings` (search) | 865 | `POST /v1/bookings` | 117 |
| `GET /v1/listings/{id}/reviews` | 663 | `POST /v1/auth/login` | **23** |
| `POST /v1/bookings/quote` | 562 | | |

## Failures found (most serious first)

| # | Failure | When it happens | What users see | Fix |
|---|---|---|---|---|
| 1 | **DB connection pool runs out** (15 per worker) | ~860 req/s on search | Requests wait 30 s, then **500** (474 failed searches); p99 30 s | Short `pool_timeout` (2–3 s) returning **503 + Retry-After**; cap concurrent requests per worker; cache search results |
| 2 | **Password hashing blocks the server** (argon2 runs on the event loop: 68 ms CPU + 64 MB per hash) | Sign-ups, logins, password changes, account deletion | Login tops out at ~23/s; *every other request* on that worker stalls (`GET /v1/me` p95 1.7 s) | Hash in a thread pool with a concurrency cap; review argon2 cost |
| 3 | **Postgres down = everything 500 after 15 s** | DB restart, failover, network blip | 15 s hang then 500 on every DB route; `/health/ready` takes 17 s to answer | Fail fast (short connect/pool timeouts) with 503 |
| 4 | **A locked table takes down search and quotes** | Long migration (`ALTER TABLE bookings`), stuck transaction | Search and quote **500** after 15 s | `lock_timeout` for the app and for migrations; run risky migrations off-peak |
| 5 | **NUL character crashes requests** (`\u0000` in any text) | Sign-up name, profile name, support message, … | **500**, or the connection is dropped | Reject `\x00` in every string field at the schema level |
| 6 | **Redis down: every request gets +2 s slower, and readiness fails** | Redis restart or blip | 2 s added to every request; QR check-in 500; `/health/ready` 503 → a load balancer would pull *all* instances at once | Shorter Redis timeouts; don't fail readiness on Redis (the API still works without it); keep PIN check-in as the fallback |
| 7 | **No request size limit** | Anyone sending big bodies | 20 MB body and 500k-key JSON are read and parsed (cheap way to burn CPU/RAM) | ~1 MB body limit (photos already go straight to S3) |
| 8 | **Redis pool too small** (10 per worker) | High load | "No connection available": cache misses fall through to the DB, making #1 worse | Raise `REDIS_MAX_CONNECTIONS`, or bound concurrency (#1) |
| 9 | **Background worker down = notifications silently pile up** | Worker crash, deploy | Emails/push stop; backlog grew ~17 events/s at 30 users; nothing alerts | Alert on outbox backlog; run Celery beat (sweeper); worker restart policy. Drains at ~60/s once back |
| 10 | **If the server's master process dies, workers keep running unsupervised** | Crash/OOM of the master | Nothing visible at first, but no more restarts or clean shutdowns | Run under a supervisor (Docker restart policy / systemd); set `WEB_CONCURRENCY` deliberately (Dockerfile default is 2) |
| 11 | **Listing detail is slow for a read** | Popular listing pages | 441 req/s, below search | It opens two DB sessions (listing + optional signed-in user/favourite); cache it, use one session |

## Fixed during testing

- **Metrics route labels dropped the `/v1` prefix**, so `/v1/legal/{doc}` and the `/legal/{doc}`
  HTML page were counted as one route. Fixed in `app/api/middleware.py` (+ regression test).
- **Outbox backlog gauge showed stale numbers after a worker died** (the dashboard said 356 while the
  database had 0). Now read fresh from the database on every scrape (`app/infra/metrics.py`).

## How to reproduce

```bash
./loadtest/k6.sh everything -e PROFILE=stress -e VUS=15     # every endpoint, up to 90 users
./loadtest/k6.sh breakpoint -e TARGET=search -e MAX_RPS=3000 # repeat per TARGET
cd backend && uv run python ../loadtest/probe_edges.py      # hostile input
./loadtest/chaos.sh                                         # while a booking load runs
```
