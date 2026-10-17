import { LineChart } from "@/components/docs/charts";
import { Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "QR & PIN access" };

// Overstay fee before GST: 5 min grace, then ₹20 per started 15-minute block.
const overstay: [number, number][] = [];
for (let m = 0; m <= 60; m += 0.5) overstay.push([m, m <= 5 ? 0 : Math.ceil((m - 5) / 15) * 20]);

export default function Access() {
  return (
    <>
      <DocHeader
        eyebrow="Core flows"
        title="QR & PIN access"
        lead="At the gate, the host scans the driver's QR code, or types a 6-digit PIN when there is no camera or no signal. Both prove the same thing: this person holds a live booking for this host's spot, right now."
      />

      <H2 id="credentials">Two credentials, two strengths</H2>
      <DataTable
        head={["", "QR code", "6-digit PIN"]}
        rows={[
          ["What it is", "A signed token with the booking id and a random one-time id (jti)", "HMAC(secret, booking id), shown as 6 digits"],
          ["Lifetime", "120 seconds; the app fetches a new one 15 s before expiry while the pass is open", "The whole booking"],
          ["Replay", "Each jti is accepted once (Redis SET NX), so a screenshot of an old QR fails", "Only valid for this host's listings and the booking's time window"],
          ["Works offline", "The driver needs a connection to refresh it", "Yes: the driver can always re-display it"],
          ["Stored secret", "None: the server signs and verifies", "None: re-derived from the booking id on every check"],
        ]}
      />
      <CodeBlock
        lang="python"
        title="app/domain/access.py"
        code={`class AccessCodeService:
    def pin_for(self, booking_id: uuid.UUID) -> str:
        # Nothing secret is stored in the database; rotating ACCESS_CODE_SECRET invalidates every PIN.
        digest = int(hmac_hex(self._secret, f"pin:{booking_id}"), 16)
        return str(digest % 10**self._pin_length).zfill(self._pin_length)

    def verify_pin(self, booking_id: uuid.UUID, pin: str) -> bool:
        return constant_time_equals(self.pin_for(booking_id), pin)`}
      />

      <H2 id="check-in">Check-in at the gate</H2>
      <Figure caption="The host's app sends the scanned token to the API. The one-time id is consumed atomically, so the same QR can never open the gate twice.">
        <Sequence
          id="qr"
          title="QR check-in sequence"
          actors={["Driver app", "Host scanner", "Parkezy API", "Redis"]}
          steps={[
            { from: 0, to: 2, label: "GET /bookings/{id}/access" },
            { from: 2, to: 0, label: "QR token (120 s) + PIN", reply: true },
            { from: 1, to: 0, label: "scan QR on screen" },
            { from: 1, to: 2, label: "POST /host/access/verify" },
            { from: 2, to: 2, label: "check signature + expiry" },
            { from: 2, to: 3, label: "SET used:qr:{jti} NX EX 120" },
            { from: 3, to: 2, label: "first use? yes", reply: true },
            { note: "booking belongs to this host · confirmed · within 15 min of start", over: [1, 2] },
            { from: 2, to: 1, label: "access granted, booking checked_in", reply: true },
          ]}
        />
      </Figure>
      <List
        items={[
          <>Check-in opens 15 minutes before the booked start and closes at the booked end.</>,
          <>Verification is rate limited per host, which matters for PINs: 6 digits are only safe if nobody can try thousands of them.</>,
          <>If Redis is unavailable, QR check-in fails rather than skip the replay check; the PIN, which needs no Redis, is the fallback at the gate.</>,
        ]}
      />

      <H2 id="overstay">Check-out and overstay</H2>
      <P>
        The driver ends the session in the app with <Code>POST /bookings/{"{id}"}/check-out</Code>. The server
        compares the time with the booked end: 5 minutes of grace, then ₹20 (plus GST) for every <i>started</i> 15-minute
        block. The final amount, receipt and ledger entries are all written in one transaction.
      </P>
      <Figure caption="Overstay fee before GST as a function of minutes past the booked end. Each step is one started 15-minute block.">
        <LineChart
          title="Overstay fee"
          series={[{ name: "overstay fee (₹, before GST)", color: "#6E5BC4", points: overstay }]}
          xLabel="minutes after the booked end"
          yLabel="fee (₹)"
          xTicks={[0, 5, 10, 20, 30, 40, 50, 60]}
          yTicks={[0, 20, 40, 60, 80]}
        />
      </Figure>
      <Callout title="No-shows">
        A confirmed booking nobody checks in to is marked as a no-show by the maintenance job once its window has
        passed. The slot is released and the payment is settled in the ledger like a completed booking.
      </Callout>

      <PrevNext slug="access" />
    </>
  );
}
