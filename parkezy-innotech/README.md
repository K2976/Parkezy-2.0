# Parkezy

Two-sided parking marketplace: drivers find and book spots; private and commercial hosts list them.

```
mobile/   Expo (React Native) app for iOS + Android — drivers and hosts in one app
backend/  FastAPI API + Celery workers (PostgreSQL/PostGIS, Redis, S3-compatible storage)
docs/     Product, architecture and decision records (ADR-008 describes this stack)
```

## Architecture

```
 Expo app ──HTTPS/JWT──► FastAPI (stateless, N workers)
                            │  same transaction
                            ├──► PostgreSQL + PostGIS ──► outbox_events
                            │      • EXCLUDE constraint = no double booking
                            │      • double-entry ledger (balanced by trigger)
                            ├──► Redis: search cache · rate limits · bloom filter · one-time QR ids
                            └──► presigned URLs ──► Backblaze B2 (phone uploads directly)
 Celery beat ──► Celery workers ──► outbox handlers ──► Resend email · Expo push · Razorpay refunds
                                 └► expire holds / unanswered requests / no-shows, reminders, cleanup
```

Key design points:
- **Server-authoritative.** Prices, GST, commission, overstay fees, PINs and QR codes are computed on the server. The app only displays them.
- **Business rules are data.** GST, commission, booking step, limits and fees live in the `platform_settings` table. Change them at runtime with `PATCH /v1/admin/settings`; the app reads them from `GET /v1/config`.
- **Nothing is lost or sent twice.** Events are written to an outbox in the same transaction as the change. Handlers are idempotent: emails are deduplicated by key, refunds are target-based, and webhooks are deduplicated with a bloom filter backed by a unique constraint.
- **SOLID.** Services depend on ports (`EmailSender`, `ObjectStorage`, `PaymentGateway`, `PushSender`, `JobQueue`, `Clock`). `app/container.py` is the only place that chooses implementations.

## External services (all free tiers)

| Need | Service | Free tier | Env vars |
|---|---|---|---|
| PostgreSQL + PostGIS | Neon (or any Postgres 16 + PostGIS) | 0.5 GB | `DATABASE_URL` |
| Redis | Redis Cloud Essentials | 30 MB | `REDIS_URL` |
| Object storage | Backblaze B2 (S3 API) | 10 GB | `S3_*` |
| Email | Resend | 3,000/month, 100/day | `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET` |
| Payments | Razorpay test mode, or `offline` (pay at venue) | free in test mode | `PAYMENT_PROVIDER`, `RAZORPAY_*` |
| Push | Expo Push Service | free | `PUSH_PROVIDER`, `EAS_PROJECT_ID` (mobile) |
| Maps (Android) | Google Maps SDK for Android | free for mobile SDK maps | `GOOGLE_MAPS_ANDROID_API_KEY` (mobile) |
| Errors | Sentry | 5k errors/month | `SENTRY_DSN` |
| Vector search | Qdrant Cloud | 1 GB | not used in v1 (reserved in `.env.example`) |

Every variable is documented in `backend/.env.example` and `mobile/.env.example`.

## Run locally

Requirements: Docker, Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# 1. Infrastructure: PostGIS, Redis, S3 (SeaweedFS standing in for B2), Mailpit (email catcher)
docker compose up -d

# 2. Backend
cd backend
cp .env.example .env            # then set JWT_SECRET and ACCESS_CODE_SECRET
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload            # API + docs at http://localhost:8000/docs
uv run celery -A app.workers.celery_app worker  # second terminal
uv run celery -A app.workers.celery_app beat    # third terminal
# Emails land in Mailpit: http://localhost:8025

# 3. Mobile
cd ../mobile
cp .env.example .env            # EXPO_PUBLIC_API_URL = http://<your-LAN-IP>:8000 for a real phone
npm install
npx expo start
```

The whole backend can also run in containers: `docker compose --profile app up --build`.

To try the app on a phone, also set `S3_PUBLIC_ENDPOINT_URL=http://<your-LAN-IP>:8333` in `backend/.env`. Photo uploads go straight from the phone to storage, so the phone must be able to reach it.

Expo Go covers browsing, booking, the QR/PIN pass, host tools and photo uploads. Online payment (Razorpay SDK) and remote push need a development build: `npx eas-cli@latest build --profile development`.

## Tests and quality

```bash
cd backend
uv run pytest            # 66 tests against real Postgres/PostGIS, Redis and S3; external SaaS is faked
uv run ruff check . && uv run ruff format --check .
PYTHONPATH=. uv run python scripts/bench.py --seed-listings 2000   # latency benchmark (needs a running API)
PYTHONPATH=. uv run python scripts/bench.py --cleanup

cd ../mobile
npx tsc --noEmit && npx expo lint && npx expo-doctor
```

The tests cover:
- the full booking lifecycle: QR check-in, replay rejection, PIN check-out, overstay fee, and ledger balance
- 12 concurrent requests for one slot, of which exactly one succeeds
- idempotent retries
- approvals and expiries
- payments, webhook deduplication, refunds and late-cancellation fees
- email retry without duplicates, and bounce suppression
- auth: refresh-token reuse detection, code lockout, and rate limits
- disputes, and account deletion with anonymisation

## Production deploy (free/cheap)

- **API:** build `backend/Dockerfile` and run it on Render, Fly or Railway. It runs migrations on start. Set `APP_ENV=production` and `TRUST_FORWARDED_FOR=true`.
- **Workers:** run the same image twice more, with `celery -A app.workers.celery_app worker` and `celery -A app.workers.celery_app beat` (exactly one beat).
- **Webhooks:** point Razorpay at `/v1/webhooks/razorpay` and Resend at `/v1/webhooks/resend`.
- **B2 bucket:** keep it private, and add a CORS rule allowing `PUT` from the app.
- **Mobile:** run `eas build` and `eas submit`. Set `EAS_PROJECT_ID` to enable push.
