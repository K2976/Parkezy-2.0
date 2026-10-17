import { BarChart } from "@/components/docs/charts";
import { Flow, Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, H3, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Security" };

export default function Security() {
  return (
    <>
      <DocHeader
        eyebrow="Quality"
        title="Security"
        lead="Layered defences: slow password hashing, short-lived tokens with stolen-token detection, rate limits that work across many servers, adaptive protection against credential stuffing, and strict input handling everywhere."
      />

      <H2 id="passwords">Passwords</H2>
      <List
        items={[
          <>Hashed with <b>argon2id</b> (memory-hard: about 70 ms of CPU and 64 MiB per hash), and re-hashed on login if the parameters are ever raised.</>,
          <>Hashing runs in a thread pool with a small concurrency cap, so a burst of sign-ins queues up instead of freezing every other request. The database connection is returned before hashing starts.</>,
          <>Unknown emails are checked against a dummy hash, so “no such account” takes as long as “wrong password”: response time does not reveal who has an account.</>,
          <>Errors are identical for both cases: <Code>401 Incorrect email or password</Code>.</>,
        ]}
      />

      <H2 id="sessions">Sessions: short access tokens, rotating refresh tokens</H2>
      <P>
        The app holds a 15-minute JWT access token in memory and a 30-day refresh token in the phone&apos;s secure
        keystore. Refresh tokens are opaque random strings, stored only as hashes, and replaced on every use. They are
        grouped into families, so reuse of an old one is a strong sign of theft.
      </P>
      <Figure caption="If an attacker steals a refresh token and either party uses it after it was rotated, the whole family is revoked and both must sign in again: the real user notices, the attacker loses access.">
        <Sequence
          id="refresh"
          title="Refresh token rotation"
          actors={["App", "Parkezy API", "Attacker"]}
          steps={[
            { from: 0, to: 1, label: "refresh with R1" },
            { from: 1, to: 0, label: "new access + R2 (R1 revoked)", reply: true },
            { from: 2, to: 1, label: "refresh with stolen R1" },
            { note: "R1 was already rotated: reuse detected", over: [1, 2] },
            { from: 1, to: 1, label: "revoke every token in the family" },
            { from: 1, to: 2, label: "401 session expired", reply: true },
            { from: 0, to: 1, label: "refresh with R2" },
            { from: 1, to: 0, label: "401: sign in again", reply: true },
          ]}
        />
      </Figure>
      <P>
        Each access token also carries the user&apos;s token version. Changing or resetting the password, deleting the account or an admin
        suspension bumps it, which signs out every device at once.
      </P>

      <H2 id="rate-limits">Rate limiting across many servers</H2>
      <P>
        Limits are kept in Redis, so they hold no matter how many API instances run. We use a sliding-window counter: a
        fixed window lets a client burst twice the limit across a window edge, while this estimate smooths the edge using
        just two counters per client.
      </P>
      <CodeBlock
        lang="python"
        title="app/infra/rate_limit.py (simplified)"
        code={`# estimated = current + previous * (1 - elapsed_fraction_of_current_window)
pipe = redis.pipeline(transaction=True)      # MULTI/EXEC: atomic across workers
pipe.incr(current_key)
pipe.expire(current_key, window_seconds * 2)
pipe.get(previous_key)
current, _, previous = await pipe.execute()
estimated = int(current) + int(previous or 0) * (1 - elapsed)
if estimated > limit:
    raise RateLimited(details={"retry_after_seconds": reset})   # 429 + Retry-After`}
      />
      <DataTable
        head={["What is limited", "Keyed by", "Why"]}
        rows={[
          ["Sign-in, sign-up, password reset", "IP (login also per email)", "The per-email limit holds even when guesses rotate through many IPs"],
          ["Reset and verification emails", "the email address", "Stops inbox bombing and protects the email quota"],
          ["Gate verification (QR / PIN)", "the host", "A 6-digit PIN is only safe if nobody can try thousands"],
          ["Booking requests", "the user", "Fair share per account"],
          ["Session refresh", "IP, with a looser limit", "Apps refresh in the background; many users can share one IP"],
        ]}
      />
      <Callout title="Client IPs">
        Behind a proxy, the client IP comes from the last <Code>X-Forwarded-For</Code> hop, the only one the client
        cannot forge, and only when the proxy is explicitly trusted. A test proves forged first hops do not dodge limits.
      </Callout>

      <H2 id="login-protection">Adaptive login protection</H2>
      <P>
        Plain rate limits treat a typo and a botnet the same. Before any password is hashed, the API scores each login
        attempt from several independent signals: recent failures for the account, the network and the device, how widely
        failures are spread across accounts and addresses, attack activity across the whole service, and whether this
        device has signed in to this account before.
      </P>
      <Figure caption="All signals are read in one atomic Redis round trip. No single signal can block a request on its own, and nothing is permanent: every counter expires." wide={false}>
        <Flow
          steps={[
            { title: "Cheap risk check", tag: "≈1 ms, before hashing", detail: "Failure history, spread of failures, service-wide attack level, known device." },
            {
              branches: [
                { title: "Low risk", tone: "success", detail: "Normal sign-in: the password is verified as usual." },
                { title: "Medium risk", tone: "warn", detail: "A challenge (CAPTCHA) is required first, or a short slow-down." },
                { title: "High risk", tone: "danger", detail: "Temporary 429 with Retry-After. The password is never hashed." },
              ],
            },
            { title: "Record the outcome", detail: "Failures feed the counters; a success clears the account's failures and remembers the device." },
          ]}
        />
      </Figure>
      <H3>Why it is cheap to defend and expensive to attack</H3>
      <Figure caption="Measured on our development machine. Rejected attempts cost about 1 ms of Redis work instead of ~68 ms of argon2. In a simulated flood of 1,000 failed logins from rotating addresses, 700 were stopped before hashing." wide={false}>
        <BarChart
          title="Cost per login attempt"
          unit="ms"
          bars={[
            { label: "risk check (Redis)", value: 1, display: "≈1" },
            { label: "argon2id password verify", value: 68, display: "≈68", tone: "muted" },
          ]}
        />
      </Figure>
      <List
        items={[
          <>Many real users behind one campus or carrier address are not penalised: only failures count, never successful sign-ins.</>,
          <>An attacker hammering someone&apos;s email can trigger challenges for that account, but the owner on their usual phone is never locked out.</>,
          <>Challenge tokens are verified with the provider on the server, accepted once, and checked for age, hostname and action. A “success” flag from the client is ignored.</>,
          <>If Redis is unavailable, a small per-server fallback still caps attempts, and real users can still sign in.</>,
        ]}
      />

      <H2 id="input">Input and transport hardening</H2>
      <DataTable
        head={["Threat", "Defence"]}
        rows={[
          ["Huge or deeply nested bodies", "Requests over 1 MiB rejected with 413 before they are read"],
          ["NUL bytes (crash Postgres text)", "Rejected in every string, query and path parameter (400) before any database work"],
          ["NaN, infinity, year 0001 dates, garbage ids", "Strict Pydantic types; all clean 4xx in our hostile-input probe"],
          ["Tampered or alg=none JWTs", "Fixed algorithm, issuer, audience and purpose; expiry checked against the server clock"],
          ["Malicious uploads", "Presigned URLs with fixed type and size; the server checks the stored object before using it"],
          ["Clickjacking, sniffing, referrer leaks", "nosniff, frame DENY, no-referrer, HSTS and no-store on every response"],
          ["Leaked secrets", "Secrets only in platform dashboards and EAS; startup refuses short JWT secrets or CORS=* in production"],
        ]}
      />

      <PrevNext slug="security" />
    </>
  );
}
