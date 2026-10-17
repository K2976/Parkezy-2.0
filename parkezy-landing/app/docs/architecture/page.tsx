import { ArchitectureDiagram, Flow } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Architecture" };

export default function Architecture() {
  return (
    <>
      <DocHeader
        eyebrow="Start here"
        title="Architecture"
        lead="One stateless API, one relational source of truth, a fast in-memory layer, and background workers for anything that can wait. Small enough for one person to run, built so each piece can scale on its own."
      />

      <Figure caption="Every box on the API tier is a Python module in one FastAPI service. They share one database transaction per request, which keeps cross-module rules (booking + payment + ledger) simple and correct.">
        <ArchitectureDiagram />
      </Figure>

      <H2 id="components">Components</H2>
      <DataTable
        head={["Layer", "Technology", "What it is responsible for"]}
        rows={[
          ["Mobile app", "Expo SDK 57, React Native, Expo Router, TanStack Query", "Map search, booking, payments, QR pass, host dashboard, QR scanner"],
          ["Landing site", "Next.js 16 on Vercel", "This website, the APK download, a health page that checks the API and database"],
          ["API", "Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async)", "89 routes: validation, auth, business rules, pricing, the booking state machine"],
          ["Database", "PostgreSQL + PostGIS on Neon", "Users, listings, slots, bookings, payments, ledger, outbox. Constraints enforce the invariants"],
          ["Cache & queue", "Redis (Redis Cloud)", "Search cache, rate-limit counters, one-time QR/challenge tokens, bloom filter, Celery broker"],
          ["Workers", "Celery worker + beat", "Deliver outbox events, expire unpaid holds, mark no-shows, reconcile payments, cleanup"],
          ["Storage", "Backblaze B2 (S3 API)", "Listing and dispute photos, uploaded directly from the phone with presigned URLs"],
          ["Providers", "Razorpay, Resend, Expo Push, Clerk", "Payments, transactional email, push notifications, Google sign-in"],
        ]}
      />

      <H2 id="request-life">Life of a request</H2>
      <P>
        What happens between a tap in the app and the response, using <Code>POST /v1/bookings</Code> as the example.
        Each step can stop the request early with a clear JSON error, so expensive work only happens for requests that
        deserve it.
      </P>
      <Figure caption="Middleware and dependencies run in this order on every request. The database is touched only after validation, authentication and rate limiting pass." wide={false}>
        <Flow
          steps={[
            { title: "Request guard", tag: "middleware", detail: "Rejects bodies over 1 MiB (413) before reading them; adds request id, timing and security headers." },
            { title: "Validation", tag: "Pydantic", detail: "Types, ranges and formats checked: bad input is a 422 with field-level messages. NUL bytes anywhere are a 400." },
            { title: "Authentication", tag: "JWT", detail: "Short-lived access token verified; token version compared so a password change signs out every device." },
            { title: "Rate limit", tag: "Redis", detail: "Sliding-window counter per user or IP. Over the limit: 429 with Retry-After." },
            { title: "Service + domain rules", tag: "one transaction", tone: "accent", detail: "Pricing, state machine, availability. Domain events are written to the outbox in the same transaction." },
            {
              branches: [
                { title: "Commit succeeds", tone: "success", detail: "201 with the booking. A worker is woken to deliver the outbox events." },
                { title: "Constraint violated", tone: "warn", detail: "Overlap or duplicate key becomes a clean 409, never a 500." },
                { title: "Database unavailable", tone: "danger", detail: "Pool wait capped at 3 s, then 503 with Retry-After instead of hanging." },
              ],
            },
          ]}
        />
      </Figure>

      <H2 id="layers">Code layout</H2>
      <P>The backend separates HTTP from business rules, so the same rules run in the API and in background workers.</P>
      <CodeBlock
        lang="text"
        title="parkezy-innotech/backend/app"
        code={`api/            # HTTP only: routes, dependencies, error mapping, middleware
  v1/          # auth, me, public, bookings, host, reviews, support, admin, webhooks …
core/          # config, security (argon2id, JWT), errors, logging, clock
domain/        # pure rules: pricing, booking_state, availability, geo, access codes
services/      # use cases: booking, payment, ledger, listing, auth, login protection …
infra/         # Redis helpers: cache, rate limiter, bloom filter, one-time tokens, metrics
integrations/  # ports to the outside: payments, email, push, storage, identity, CAPTCHA
workers/       # Celery tasks: outbox processor, maintenance, reconciliation
container.py   # composition root: builds every dependency once, tests swap pieces`}
      />

      <H2 id="deployment">Deployment</H2>
      <DataTable
        head={["Piece", "Where it runs", "Notes"]}
        rows={[
          ["API + worker", "Render (Docker, Oregon)", "One container runs uvicorn and the Celery worker, with migrations applied on start"],
          ["Database", "Neon Postgres (us-east-2)", "Pooled connections via PgBouncer"],
          ["Redis", "Redis Cloud (us-east-2)", "Next to the database, so a login's two Redis round trips stay short"],
          ["Landing + docs", "Vercel", "Static pages plus one server route for the health check"],
          ["Android app", "EAS Build", "Release APK; secrets live in EAS environment variables, never in the repo"],
        ]}
      />
      <Callout title="Why one container for API and worker?">
        The free hosting plan has no separate background workers. The start script runs both and stops the API if the
        worker dies, so the platform restarts the pair together instead of silently serving requests whose emails would
        never be sent. On a paid plan the worker moves to its own service with no code change.
      </Callout>

      <H2 id="config">Configuration and secrets</H2>
      <List
        items={[
          <>Infrastructure settings come from environment variables, validated at startup. The app refuses to boot with, say, Resend selected but no key, or short JWT secrets in production.</>,
          <>Business rules (GST, commission, hold times, overstay fees) live in a <Code>platform_settings</Code> table, so an admin can change them without a deploy.</>,
          <>No key of any kind is committed to the repository: deployment files mark secrets <Code>sync: false</Code> and they are set in each platform&apos;s dashboard.</>,
        ]}
      />

      <PrevNext slug="architecture" />
    </>
  );
}
