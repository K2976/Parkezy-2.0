import { BarChart, SplitBar } from "@/components/docs/charts";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext, Stats } from "@/components/docs/ui";

export const metadata = { title: "Load tests & reliability" };

const fixed = <span className="font-semibold text-[#2F8A6A]">Fixed</span>;
const partly = <span className="font-semibold text-amber-700">Partly</span>;
const open = <span className="font-semibold text-[#666173]">Open</span>;

export default function Reliability() {
  return (
    <>
      <DocHeader
        eyebrow="Quality"
        title="Load tests & reliability"
        lead="We pushed the backend until it broke, on purpose: every endpoint under load, races on a single slot, hostile input, killed workers, and a database and Redis taken away mid-test. This page shows what held, what broke, and what we changed."
      />

      <Stats
        items={[
          { value: "69,424", label: "requests across all 89 routes" },
          { value: "621", label: "complete user journeys, up to 90 concurrent users" },
          { value: "0", label: "wrong answers and 0 server errors under load" },
          { value: "0 / 1,957", label: "requests failed while API workers were being killed" },
        ]}
      />

      <H2 id="setup">How we tested</H2>
      <List
        items={[
          <>k6 scripts drive the real API: 500 drivers, 50 hosts and 1,000 listings in an isolated database.</>,
          <>Profiles: full user journeys, breakpoint ramps per endpoint, a slot race, and chaos (killing workers, stopping Postgres and Redis).</>,
          <>A Python probe sends hostile input to every route: malformed and deep JSON, NaN and 1e308, year 0001, NUL bytes, tampered and <Code>alg=none</Code> tokens, path traversal.</>,
          <>Local machine (16 cores, 4 API workers, k6 on the same box), so absolute numbers are pessimistic; where and how things break carries over.</>,
        ]}
      />
      <CodeBlock
        lang="text"
        title="loadtest/"
        code={`./loadtest/k6.sh everything -e PROFILE=stress -e VUS=15      # every endpoint, up to 90 users
./loadtest/k6.sh breakpoint -e TARGET=search -e MAX_RPS=3000  # ramp one endpoint until it breaks
./loadtest/k6.sh race                                          # many drivers, one slot
uv run python ../loadtest/probe_edges.py                       # hostile input
./loadtest/chaos.sh                                            # kill workers during load`}
      />

      <H2 id="capacity">Capacity per endpoint</H2>
      <Figure caption="Peak sustained requests per second, 4 workers. Reads are fast; login is deliberately slow because of argon2 password hashing (measured before hashing moved off the event loop)." wide={false}>
        <BarChart
          title="Peak sustained requests per second"
          unit="req/s"
          bars={[
            { label: "GET /v1/config", value: 1634 },
            { label: "GET /v1/me", value: 1009 },
            { label: "GET /v1/listings (search)", value: 865 },
            { label: "GET /listings/{id}/reviews", value: 663 },
            { label: "POST /v1/bookings/quote", value: 562 },
            { label: "GET /v1/listings/{id}", value: 441 },
            { label: "GET /v1/bookings", value: 266 },
            { label: "POST /v1/bookings", value: 117 },
            { label: "POST /v1/auth/login", value: 23, tone: "danger" },
          ]}
        />
      </Figure>

      <H2 id="correctness">Correctness under pressure</H2>
      <Figure caption="100 drivers booking one slot for the same window at the same instant." wide={false}>
        <SplitBar
          title="Slot race"
          parts={[
            { label: "booked", value: 1, color: "#2F8A6A" },
            { label: "clean 409 slot taken", value: 99, color: "#C9C1E8" },
          ]}
        />
      </Figure>
      <DataTable
        head={["Scenario", "Result"]}
        rows={[
          ["20 parallel retries with one Idempotency-Key", "1 booking"],
          ["20 parallel sign-ups with one email", "1 account, 19 × 409"],
          ["Hostile input on every route", "all clean 4xx, no 500s"],
          ["Brute-force login", "429 with Retry-After after the limit"],
          ["API worker killed under load", "respawned in seconds, 0 of 1,957 requests failed"],
          ["Database during the whole run", "0 deadlocks, never more than 6 queries active at once"],
        ]}
      />

      <H2 id="failures">What broke, and what we did about it</H2>
      <P>
        Finding these was the point of the exercise. The fixed ones each have a regression test, so they cannot quietly
        come back.
      </P>
      <DataTable
        head={["#", "Failure under load", "Fix", "Status"]}
        rows={[
          ["1", "Search at ~860 req/s ran out of DB connections: requests waited 30 s, then 500", "Pool wait capped at 3 s, answered as 503 + Retry-After; search cache", fixed],
          ["2", "Password hashing ran on the event loop: login capped at ~23/s and every other request stalled", "Hashing in a bounded thread pool; DB connection released before hashing", fixed],
          ["3", "Postgres down: every request hung 15 s, then 500", "Short connect and pool timeouts, 503 instead of 500", fixed],
          ["4", "A locked table made search and quotes 500", "Lock waits classified and answered as 503", fixed],
          ["5", "A NUL character in any text crashed the request", "Rejected everywhere with 400 before touching the database", fixed],
          ["6", "Redis down: readiness failed, so a load balancer would pull every instance", "Readiness stays up as “degraded”; Redis-backed features degrade instead of failing", fixed],
          ["7", "No body size limit: 20 MB bodies were parsed", "1 MiB cap, refused before reading", fixed],
          ["8", "Redis pool too small at peak, pushing load onto the database", "Pool size is configurable; to be sized for production traffic", partly],
          ["9", "Worker down meant notifications silently piled up", "Outbox backlog and dead letters exposed in /metrics; alerts still to be wired", partly],
          ["10", "If the server's master process died, workers ran unsupervised", "Container restarts the pair together on Render", partly],
          ["11", "Listing detail slower than search", "Cache it and use one session", open],
        ]}
      />

      <H2 id="observability">Observability</H2>
      <P>
        The API exposes Prometheus metrics at <Code>/metrics</Code> (behind a bearer token): request rate and latency per
        route template, outbox backlog and dead letters, password-hashing latency, and login-protection outcomes. Every
        request is logged as one JSON line with a request id, which is also returned to the client in{" "}
        <Code>X-Request-ID</Code> for support.
      </P>
      <CodeBlock
        lang="text"
        title="/metrics (format, illustrative values)"
        code={`parkezy_http_requests_total{method="GET",route="/v1/listings",status="200"} 51234
parkezy_http_request_duration_seconds_bucket{method="POST",route="/v1/bookings",le="0.25"} 9112
parkezy_outbox_pending 0
parkezy_outbox_dead_letters 0
parkezy_login_attempts_total{outcome="throttled"} 0`}
      />
      <Callout title="Health checks" tone="success">
        <Code>/health/live</Code> answers instantly even with every dependency down (is the process alive?).{" "}
        <Code>/health/ready</Code> requires the database but only reports Redis, so a Redis blip degrades features
        instead of taking the whole service out of rotation.
      </Callout>

      <PrevNext slug="reliability" />
    </>
  );
}
