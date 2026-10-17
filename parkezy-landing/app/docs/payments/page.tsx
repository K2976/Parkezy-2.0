import { Flow, Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, H3, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Payments & ledger" };

const rupees = (n: string) => <span className="font-mono tabular-nums">₹{n}</span>;

export default function Payments() {
  return (
    <>
      <DocHeader
        eyebrow="Core flows"
        title="Payments & ledger"
        lead="Money has to be right every time, including when networks drop, webhooks arrive twice or the gateway is slow. Razorpay moves the money; a double-entry ledger in Postgres records exactly who is owed what."
      />

      <H2 id="flow">Paying for a booking</H2>
      <Figure caption="The app never decides that a payment succeeded. The server checks a signature from Razorpay, and a signed webhook confirms it independently. Whichever arrives first wins; the second is a no-op.">
        <Sequence
          id="pay"
          title="Payment sequence"
          actors={["Driver app", "Parkezy API", "Razorpay", "Worker"]}
          steps={[
            { from: 0, to: 1, label: "POST /bookings/{id}/payment" },
            { from: 1, to: 2, label: "create order (amount in paise)" },
            { from: 1, to: 0, label: "order_id + public key id", reply: true },
            { from: 0, to: 2, label: "Razorpay checkout (UPI / card)" },
            { from: 2, to: 0, label: "payment_id + signature", reply: true },
            { from: 0, to: 1, label: "POST …/payment/confirm" },
            { note: "HMAC-SHA256(order_id | payment_id) checked server-side", over: [1, 2] },
            { from: 2, to: 1, label: "webhook payment.captured (signed)" },
            { from: 1, to: 1, label: "capture once, confirm booking" },
            { from: 3, to: 2, label: "every 5 min: reconcile stuck orders" },
          ]}
        />
      </Figure>

      <H2 id="webhooks">Webhooks: verified, de-duplicated, idempotent</H2>
      <Flow
        steps={[
          { title: "Verify signature", tag: "HMAC-SHA256", detail: "Computed over the raw body with the webhook secret and compared in constant time. A bad signature is a 401 and nothing else happens." },
          { title: "Bloom filter pre-check", tag: "Redis bitmap", detail: "Answers “definitely new” or “maybe seen” in microseconds. It is only a fast path, never the source of truth." },
          { title: "Record the event id", tag: "webhook_events", detail: "A unique row per gateway event id. A duplicate insert means we already processed it, so we return 200 and stop." },
          { title: "Apply once", tone: "accent", detail: "Capture or fail the payment under a row lock; if the checkout confirmation already captured it, this is a no-op." },
        ]}
      />
      <CodeBlock
        lang="python"
        title="app/integrations/payments.py"
        code={`def _hmac_ok(secret: str, message: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")   # constant time

def verify_checkout_signature(self, *, order_id, payment_id, signature) -> bool:
    return _hmac_ok(self._key_secret, f"{order_id}|{payment_id}".encode(), signature)

def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool:
    return _hmac_ok(self._webhook_secret, body, signature)`}
      />

      <H3>Reconciliation</H3>
      <P>
        If both the app confirmation and the webhook are lost, a booking could stay unpaid even though the driver paid.
        Every 5 minutes a job asks Razorpay what it actually recorded for orders still open after 5 minutes, and
        captures or fails them. The gateway is the source of truth for whether money moved.
      </P>

      <H2 id="ledger">Double-entry ledger</H2>
      <P>
        Every money event is a ledger transaction: a set of entries that must sum to exactly zero (debits positive,
        credits negative). Balances such as “what can this host withdraw” are sums over entries, never a number that
        gets overwritten.
      </P>
      <H3>Worked example: a real booking from our tests</H3>
      <P>
        2 hours at ₹45/hour on a private listing: subtotal {rupees("90.00")}, GST 18% {rupees("16.20")}, driver pays{" "}
        {rupees("106.20")}. On completion the ledger records:
      </P>
      <DataTable
        head={["Account", "Debit (+)", "Credit (−)", "Meaning"]}
        rows={[
          [<b key="a">driver_payments</b>, rupees("106.20"), "", "cash received through the gateway"],
          [<b key="b">gst_payable</b>, "", rupees("16.20"), "tax owed to the government"],
          [<b key="c">platform_revenue</b>, "", rupees("13.50"), "15% commission on ₹90"],
          [<b key="d">host_payable</b>, "", rupees("76.50"), "the host's earnings"],
          [<span key="e" className="font-semibold text-[#2F8A6A]">sum</span>, rupees("106.20"), rupees("106.20"), "balanced: debits = credits"],
        ]}
      />
      <P>The database itself refuses an unbalanced transaction, even if application code had a bug:</P>
      <CodeBlock
        lang="sql"
        title="migrations/versions/0001_initial.py"
        code={`-- Double-entry invariant: every transaction must balance to zero.
CREATE FUNCTION ledger_txn_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT COALESCE(SUM(amount), 0) FROM ledger_entries WHERE txn_id = NEW.txn_id) <> 0 THEN
        RAISE EXCEPTION 'ledger transaction % does not balance', NEW.txn_id;
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER trg_ledger_balanced AFTER INSERT ON ledger_entries
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_txn_balanced();`}
      />
      <Callout title="Why deferred?">
        A transaction is several rows. A deferred constraint trigger checks the sum at <Code>COMMIT</Code>, after all
        entries are inserted, so a half-written transaction can never be saved.
      </Callout>

      <H2 id="payouts">Host payouts and other events</H2>
      <List
        items={[
          <>Pay-at-venue bookings book the cash to <Code>host_collected</Code> instead, so the host owes the commission rather than being owed the fare.</>,
          <>Late cancellations post the kept amount, split between the platform and the host the same way.</>,
          <>A withdrawal moves money <Code>host_payable → payouts_pending</Code>; marking it paid moves it to <Code>platform_bank</Code>; a rejected payout returns it.</>,
          <>Refunds are target-based: the job brings a booking&apos;s total refunded amount up to a target, so a retried refund never pays out more than once.</>,
        ]}
      />

      <PrevNext slug="payments" />
    </>
  );
}
