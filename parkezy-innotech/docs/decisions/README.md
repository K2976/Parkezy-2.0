# Architecture Decision Records

Format: Context · Decision · Consequences · Status. Add new ADRs as `ADR-0NN-title.md` files in this folder and list them here.

| ID | Title | Status |
|---|---|---|
| ADR-001 | Keep native iOS SwiftUI + Supabase | **Superseded** by ADR-008 |
| ADR-002 | Authoritative business rules live on the server, not the client | **Accepted** (implemented in FastAPI, ADR-008) |
| ADR-003 | Normalize slots into a table; use PostGIS and `timestamptz` | **Accepted** (implemented) |
| ADR-004 | Single unified bookings model with status enum; drop legacy `parking_spots` flow | **Accepted** (implemented) |
| ADR-005 | Per-environment `.xcconfig`; secrets never in source | Proposed |
| ADR-006 | Payment provider | **Accepted**: Razorpay behind a port, plus pay-at-venue mode (`PAYMENT_PROVIDER`) |
| ADR-008 | FastAPI backend + Expo (React Native) app, free-tier infrastructure | **Accepted** (owner decision, 2026-10-13) |
| ADR-007 | Minimum iOS version | Open (Q-04) |

## ADR-001 — Keep SwiftUI + Supabase
**Context:** The legacy app is SwiftUI on Supabase, previously Firebase and Django (see [data-architecture](../architecture/data-architecture.md#migration-history)). The owner chose to keep the stack. **Decision:** Native iOS SwiftUI client; Supabase Auth, Postgres (RLS, RPC), Storage, Realtime, Edge Functions. **Consequences:** No custom server to operate; security depends on RLS quality; Android/web would need a separate client.

## ADR-002 — Server-authoritative rules
**Context:** The client computes prices, PINs, occupancy and capabilities (SEC-02/03/08, BUG-06). **Decision:** Mutations go through `SECURITY DEFINER` RPCs/Edge Functions that validate and compute; tables are read-mostly for clients; privileged columns are not writable. **Consequences:** More SQL to write/test (pgTAP); clients become thin; business rules testable independently of the app.

## ADR-008 — FastAPI + Expo on free-tier infrastructure
**Context:** The owner chose a Python backend and a cross-platform app; India is Android-heavy, so iOS-only SwiftUI limited reach. The owner also required free-tier services for now, Backblaze B2 for object storage, and Qdrant only if vector search becomes necessary.
**Decision:** `backend/` is FastAPI + SQLAlchemy (async) + Alembic on PostgreSQL/PostGIS; Redis for cache, rate limits, bloom filters and the Celery broker; Celery workers + beat for the transactional outbox, expiries, reminders, refunds and cleanup; self-issued JWT auth with rotating refresh tokens; S3 API to Backblaze B2; Resend (or SMTP) for email; Expo Push; Razorpay (test mode) or pay-at-venue. `mobile/` is Expo SDK 57 with Expo Router and TanStack Query. Business rules live in the `platform_settings` table; infrastructure config in `.env`. Qdrant is not used in v1 (search is PostGIS + filters).
**Consequences:** One backend to operate (API, worker, beat). Double booking is prevented by a Postgres exclusion constraint, not application code. Supabase is no longer required; any Postgres with PostGIS works (Neon free tier recommended because it does not hibernate permanently). Live Activities/widgets stay deferred (need native targets). Online payment needs an EAS development build (Razorpay SDK is native).
