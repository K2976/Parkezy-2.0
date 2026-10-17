import { SplitBar } from "@/components/docs/charts";
import { BookingStateMachine, Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, H3, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Booking engine" };

export default function Booking() {
  return (
    <>
      <DocHeader
        eyebrow="Core flows"
        title="Booking engine"
        lead="The heart of Parkezy: turning a driver's request into a guaranteed slot. Three ideas make it safe: a strict state machine, a database constraint that makes double booking impossible, and idempotent requests that make retries harmless."
      />

      <H2 id="lifecycle">The booking lifecycle</H2>
      <P>
        A booking can only move along the arrows below. The rules live in one place (<Code>domain/booking_state.py</Code>),
        so the API, the background jobs and the admin tools can never disagree about what is allowed.
      </P>
      <Figure caption="Hosts either auto-accept or approve each request. Unpaid holds expire after 10 minutes, unanswered requests after 30, and confirmed bookings nobody checks in to are marked no-show by the maintenance job.">
        <BookingStateMachine />
      </Figure>
      <CodeBlock
        lang="python"
        title="app/domain/booking_state.py (simplified)"
        code={`TRANSITIONS: dict[S, frozenset[S]] = {
    S.PENDING_APPROVAL: frozenset({S.PENDING_PAYMENT, S.CONFIRMED, S.REJECTED, S.CANCELLED, S.EXPIRED}),
    S.PENDING_PAYMENT: frozenset({S.CONFIRMED, S.CANCELLED, S.EXPIRED}),
    S.CONFIRMED: frozenset({S.CHECKED_IN, S.CANCELLED, S.EXPIRED}),
    S.CHECKED_IN: frozenset({S.COMPLETED}),
    S.COMPLETED: frozenset(),  # terminal states accept nothing
    ...
}

def ensure_transition(current, target) -> None:
    if not can_transition(current, target):
        raise Conflict(f"Booking cannot move from {current} to {target}", code="invalid_booking_transition")`}
      />

      <H2 id="request-flow">From tap to confirmed</H2>
      <Figure caption="Happy path for an auto-accepted listing with online payment. The price is always computed by the server; the app only displays it.">
        <Sequence
          id="book"
          title="Booking sequence"
          actors={["Driver app", "API", "Postgres", "Razorpay"]}
          steps={[
            { from: 0, to: 1, label: "POST /v1/bookings/quote" },
            { from: 1, to: 0, label: "subtotal + 18% GST", reply: true },
            { from: 0, to: 1, label: "POST /v1/bookings + Idempotency-Key" },
            { from: 1, to: 2, label: "INSERT booking (pending_payment)" },
            { note: "exclusion constraint checks overlap atomically", over: [1, 2] },
            { from: 2, to: 1, label: "ok, or overlap violation", reply: true },
            { from: 1, to: 0, label: "201 booking (slot held 10 min)", reply: true },
            { from: 0, to: 1, label: "POST /bookings/{id}/payment" },
            { from: 1, to: 3, label: "create order" },
            { from: 0, to: 3, label: "checkout (card / UPI)" },
            { from: 0, to: 1, label: "payment/confirm (signed result)" },
            { from: 1, to: 2, label: "confirmed + outbox events" },
          ]}
        />
      </Figure>

      <H2 id="no-double-booking">Zero double booking, enforced by Postgres</H2>
      <P>
        Checking availability in application code and then inserting is a race: two requests can both see the slot as
        free. Instead, the database refuses the second row. Each booking stores its time window as a range, and an
        exclusion constraint forbids two live bookings on the same slot whose ranges overlap.
      </P>
      <CodeBlock
        lang="sql"
        title="migrations/versions/0001_initial.py"
        code={`-- The core integrity guarantee: one slot can never hold two overlapping live bookings.
CONSTRAINT ex_bookings_no_overlap EXCLUDE USING gist (slot_id WITH =, period WITH &&)
    WHERE (status IN ('pending_approval', 'pending_payment', 'confirmed', 'checked_in'))`}
      />
      <P>
        Cancelled, rejected and expired bookings fall outside the <Code>WHERE</Code> clause, so their time frees up
        immediately. The service turns the violation into a clean <Code>409</Code>; when the driver did not choose a
        specific slot, it quietly retries with the next free one.
      </P>
      <H3>Measured: 100 drivers, one slot, the same instant</H3>
      <Figure caption="k6 race test: 100 virtual drivers booked the same single slot for the same window at once. The constraint let exactly one through.">
        <SplitBar
          title="Race test result"
          parts={[
            { label: "booked (201)", value: 1, color: "#2F8A6A" },
            { label: "rejected cleanly (409 slot taken)", value: 99, color: "#C9C1E8" },
          ]}
        />
      </Figure>

      <H2 id="idempotency">Safe retries with Idempotency-Key</H2>
      <P>
        Phones lose connections mid-request. If the app retries a booking after a timeout, the driver must not end up
        with two bookings. Every <Code>POST /v1/bookings</Code> carries an <Code>Idempotency-Key</Code> header, and a
        unique constraint on <Code>(driver_id, idempotency_key)</Code> means a repeat returns the original booking.
      </P>
      <DataTable
        head={["Scenario", "Result"]}
        rows={[
          ["20 parallel retries with one Idempotency-Key", "1 booking, every response points at it"],
          ["20 parallel sign-ups with one email", "1 account, 19 × 409"],
          ["Same key reused for a different booking", "409 idempotency_mismatch: a key can never be recycled by accident"],
        ]}
      />

      <H2 id="pricing">Pricing, server-side</H2>
      <List
        items={[
          <>Times align to 15-minute steps; bookings run from 30 minutes to 7 days, up to 30 days ahead.</>,
          <>Price is pro-rata by the minute, with an optional daily cap per 24-hour block. All money is <Code>Decimal</Code>, rounded half-up to the paisa.</>,
          <>GST (18%) is added on the subtotal; the platform commission (15% private, 12% commercial) comes out of the host&apos;s share, not the driver&apos;s price.</>,
          <>Free cancellation until 60 minutes before the start; after that 25% of the subtotal is kept.</>,
          <>Overstay: 5 minutes of grace, then ₹20 (plus GST) for every started 15-minute block.</>,
        ]}
      />
      <Callout title="Rules are data, not code">
        Every number above lives in the <Code>platform_settings</Code> table and is served to the app by{" "}
        <Code>GET /v1/config</Code>, so the app and the server always use the same rules, and an admin can change them
        without shipping a new APK.
      </Callout>

      <PrevNext slug="booking" />
    </>
  );
}
