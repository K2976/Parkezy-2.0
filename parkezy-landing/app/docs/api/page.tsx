import { BarChart } from "@/components/docs/charts";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "API reference" };

export default function Api() {
  return (
    <>
      <DocHeader
        eyebrow="Clients"
        title="API reference"
        lead="A versioned JSON REST API at https://parkezy-api.onrender.com/v1. Every response, success or error, follows one contract, so clients handle the whole API the same way."
      />

      <H2 id="groups">Endpoint groups</H2>
      <Figure caption="All 89 routes by group. Host tools and admin operations make up almost half of the surface; the driver flow itself is compact." wide={false}>
        <BarChart
          title="Routes per group"
          unit="routes"
          bars={[
            { label: "/v1/host", value: 22 },
            { label: "/v1/admin", value: 15, tone: "muted" },
            { label: "/v1/bookings", value: 14 },
            { label: "/v1/me", value: 11 },
            { label: "/v1/auth", value: 10 },
            { label: "/v1/listings", value: 3 },
            { label: "reviews · uploads · notifications · disputes · support", value: 10, display: "2 each" },
            { label: "health · config · legal", value: 4, tone: "muted" },
          ]}
        />
      </Figure>
      <DataTable
        head={["Group", "Highlights"]}
        rows={[
          [<Code key="a">/v1/auth</Code>, "register, login, Google sign-in, refresh, logout, verify email, forgot / reset / change password"],
          [<Code key="b">/v1/listings</Code>, "radius search with filters, listing detail, reviews (public, no sign-in needed)"],
          [<Code key="c">/v1/bookings</Code>, "quote, create (Idempotency-Key), list, cancel, access pass, check-out, extend, review, receipt (JSON and PDF), payment and confirm"],
          [<Code key="d">/v1/host</Code>, "listings and slots, photos, approve / reject, gate verification, dashboard, payout account, payouts"],
          [<Code key="e">/v1/me</Code>, "profile, become host, push tokens, notification preferences, favourites, delete account"],
          [<Code key="f">/v1/admin</Code>, "users, suspensions, disputes, payouts, platform settings, outbox dead letters"],
          [<Code key="g">/v1/uploads</Code>, "presigned upload, then complete (server checks size and type)"],
          [<Code key="h">/v1/config</Code>, "the live business rules the app uses: GST, booking limits, fees"],
        ]}
      />

      <H2 id="example">Example: quote then book</H2>
      <CodeBlock
        lang="http"
        title="request"
        code={`POST /v1/bookings/quote
Content-Type: application/json

{ "listing_id": "01a148ee-…", "starts_at": "2026-10-17T11:00:00Z", "ends_at": "2026-10-17T13:00:00Z" }`}
      />
      <CodeBlock
        lang="json"
        title="200 OK (values from a real test booking)"
        code={`{
  "listing_id": "01a148ee-…",
  "slot_id": null,
  "starts_at": "2026-10-17T11:00:00Z",
  "ends_at": "2026-10-17T13:00:00Z",
  "duration_minutes": 120,
  "hourly_rate": "45.00",
  "subtotal": "90.00",
  "tax_rate": "0.18",
  "tax_amount": "16.20",
  "total": "106.20",
  "currency": "INR",
  "payment_mode": "online",
  "requires_approval": false,
  "available": true
}`}
      />
      <CodeBlock
        lang="http"
        title="request"
        code={`POST /v1/bookings
Authorization: Bearer <access token>
Idempotency-Key: 9f1c2b7e4d…          # same key again = same booking back

{ "listing_id": "01a148ee-…", "starts_at": "2026-10-17T11:00:00Z", "ends_at": "2026-10-17T13:00:00Z" }`}
      />
      <P>
        Money is always a decimal string (never a float), times are ISO 8601 in UTC, and ids are UUIDv7: unique without
        coordination, and roughly time-ordered.
      </P>

      <H2 id="errors">The error contract</H2>
      <CodeBlock
        lang="json"
        title="every error looks like this"
        code={`{
  "error": {
    "code": "slot_unavailable",
    "message": "This slot was just booked for that time",
    "details": null
  }
}`}
      />
      <DataTable
        head={["Status", "Meaning", "Example codes"]}
        rows={[
          ["400", "Malformed request", "invalid_characters (NUL byte)"],
          ["401", "Not signed in, or a bad token", "not_authenticated, invalid_credentials, token_expired"],
          ["403", "Signed in but not allowed", "not_a_host, email_not_verified, own_listing, challenge_required"],
          ["404", "Not found (also for things you may not see)", "not_found"],
          ["409", "Conflicts with current state", "slot_unavailable, no_availability, idempotency_mismatch, invalid_booking_transition"],
          ["413", "Body over 1 MiB", "payload_too_large"],
          ["422", "Validation or a business rule failed; details explain", "validation_failed, start_too_far"],
          ["429", "Rate limited; honour Retry-After", "rate_limited"],
          ["503", "Temporarily unavailable; retry after Retry-After", "database_busy, database_unavailable"],
        ]}
      />
      <Callout title="Client rules of thumb">
        <List
          items={[
            <>Branch on <Code>error.code</Code>, never on the message text: messages may change, codes are stable.</>,
            <>Retry 429 and 503 only after <Code>Retry-After</Code>; retry booking creation with the same Idempotency-Key.</>,
            <>Send <Code>X-Request-ID</Code> or read it from the response when reporting a problem; it ties the request to our logs.</>,
          ]}
        />
      </Callout>

      <H2 id="health">Health and status</H2>
      <CodeBlock
        lang="http"
        title="readiness"
        code={`GET /health/ready

{ "status": "ok", "checks": { "database": "ok", "redis": "ok" } }`}
      />
      <P>
        Interactive API docs (<Code>/docs</Code>) are switched off in production to keep the attack surface small; they
        are available in local and staging environments.
      </P>

      <PrevNext slug="api" />
    </>
  );
}
