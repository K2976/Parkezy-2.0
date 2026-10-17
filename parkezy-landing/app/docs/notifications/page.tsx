import { LineChart } from "@/components/docs/charts";
import { Flow, Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Outbox & notifications" };

// Retry delay from app/workers/outbox_processor.py: min(15 s * 2^(n-1), 1 h), jittered to 75-100%.
const delayMin = (n: number) => Math.min(15 * 2 ** (n - 1), 3600) / 60;
const attempts = Array.from({ length: 10 }, (_, i) => i + 1);

export default function Notifications() {
  return (
    <>
      <DocHeader
        eyebrow="Core flows"
        title="Outbox & notifications"
        lead="When a booking is confirmed, the driver gets an email, a push notification and an in-app message, even if the email provider is down at that moment. The transactional outbox makes that reliable without slowing the request down."
      />

      <H2 id="problem">The dual-write problem</H2>
      <P>
        Saving a booking and sending an email are two systems. Send first and the save may fail: an email for a booking
        that does not exist. Save first and the process may crash before sending: a booking nobody hears about. The
        outbox removes the second system from the request entirely.
      </P>
      <Figure caption="The event row is written in the same transaction as the state change, so it exists if and only if the change committed. Delivery happens afterwards, in a worker.">
        <Flow
          steps={[
            { title: "BEGIN", tag: "one Postgres transaction", detail: "Inside the request that changes state." },
            {
              branches: [
                { title: "Update the booking", tone: "accent", detail: "status → confirmed" },
                { title: "INSERT outbox_events", tone: "accent", detail: "type booking.confirmed, payload, available_at = now" },
              ],
            },
            { title: "COMMIT", tone: "success", detail: "Both rows exist, or neither does. The API answers the driver immediately." },
            { title: "Worker delivers", tag: "Celery", detail: "Woken right after commit; a sweep every 30 s is the safety net if the wake-up is lost." },
            {
              branches: [
                { title: "Email", detail: "Rendered template via Resend" },
                { title: "Push", detail: "Expo push to the user's devices" },
                { title: "In-app", detail: "Row in the notifications inbox" },
              ],
            },
          ]}
        />
      </Figure>

      <H2 id="claiming">Many workers, no double delivery</H2>
      <P>
        Workers claim events with a lease. Rows are locked with <Code>SKIP LOCKED</Code>, so concurrent workers grab
        different rows instead of waiting on each other, and <Code>available_at</Code> is pushed into the future before
        the lock is released. If a worker crashes mid-delivery the lease simply runs out and another worker retries the
        event. Delivery is at-least-once, so every handler is idempotent.
      </P>
      <CodeBlock
        lang="python"
        title="app/workers/outbox_processor.py (simplified)"
        code={`rows = (await session.execute(
    select(OutboxEvent)
    .where(
        OutboxEvent.processed_at.is_(None),
        OutboxEvent.available_at <= now,
        OutboxEvent.attempts < self._max_attempts,   # 10, then it is a dead letter
    )
    .order_by(OutboxEvent.available_at)
    .limit(self._batch)                      # 50 per batch
    .with_for_update(skip_locked=True)       # other workers skip these rows
)).scalars()
for row in rows:
    row.attempts += 1
    row.available_at = now + backoff(row.attempts, self._base, self._max)   # the lease
await session.commit()`}
      />

      <H2 id="retries">Retries with exponential backoff and jitter</H2>
      <P>
        A failed delivery is retried after 15 s, 30 s, 1 min, 2 min … capped at one hour, for up to 10 attempts. Each
        delay is randomised to 75–100% of its value, so thousands of events that failed together during a provider outage
        do not all retry in the same second and trip its rate limit again.
      </P>
      <Figure caption="Retry delay per attempt. The band is the jitter range; after the 10th failed attempt the event goes to the dead-letter queue, where an admin can inspect and retry it.">
        <LineChart
          title="Outbox retry backoff"
          series={[
            {
              name: "delay before next attempt (max)",
              color: "#6E5BC4",
              points: attempts.map((n) => [n, delayMin(n)]),
              area: attempts.map((n) => [n, delayMin(n) * 0.75]),
            },
          ]}
          xLabel="attempt number"
          yLabel="minutes"
          xTicks={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
          yTicks={[0, 15, 30, 45, 60]}
        />
      </Figure>

      <H2 id="events">Events and channels</H2>
      <DataTable
        head={["Event", "Who hears about it"]}
        rows={[
          [<Code key="1">booking.requested</Code>, "host: a new request to approve"],
          [<Code key="2">booking.awaiting_payment</Code>, "driver: approved, pay within the hold"],
          [<Code key="3">booking.confirmed</Code>, "driver and host: email, push and inbox"],
          [<Code key="4">booking.checked_in · ending_soon · extended</Code>, "driver: session updates, a reminder 15 minutes before the end"],
          [<Code key="5">booking.completed</Code>, "driver: receipt; host: earnings"],
          [<Code key="6">booking.cancelled · rejected · expired</Code>, "the other party, plus refunds where due"],
          [<Code key="7">dispute.created · dispute.updated · payout.paid · payout.rejected</Code>, "the people involved"],
          [<Code key="8">auth.verification_code · auth.password_changed · account.deleted</Code>, "account security emails"],
        ]}
      />

      <H2 id="email">Email delivery</H2>
      <Figure caption="Resend reports what happened to each email through a signed webhook.">
        <Sequence
          id="mail"
          title="Email sequence"
          actors={["Worker", "Resend", "Inbox", "Parkezy API"]}
          steps={[
            { from: 0, to: 1, label: "send (HTML + text templates)" },
            { from: 1, to: 0, label: "message id", reply: true },
            { from: 1, to: 2, label: "deliver" },
            { from: 1, to: 3, label: "webhook: delivered / bounced" },
            { note: "bounced or complained → address suppressed", over: [2, 3] },
          ]}
        />
      </Figure>
      <List
        items={[
          <>Bounced and complained addresses are suppressed, so we stop sending to them and protect the sending domain&apos;s reputation.</>,
          <>Verification codes are scrubbed from the stored outbox payload once sent; no secret sits in the database longer than needed.</>,
          <>Users choose which channels they want per category in notification preferences; security emails always go out.</>,
        ]}
      />
      <Callout title="Watching the backlog" tone="warn">
        If the worker stops, nothing fails loudly; events just pile up. <Code>/metrics</Code> exposes the pending and
        dead-letter counts, read fresh from the database on every scrape, so an alert can fire on a growing backlog.
      </Callout>

      <PrevNext slug="notifications" />
    </>
  );
}
