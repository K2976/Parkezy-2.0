import Link from "next/link";

import { Callout, DataTable, DocHeader, H2, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "System design notes" };

const CHAPTERS: [string, string, string, string][] = [
  ["1", "Scale from zero to millions", "Stateless API behind a load balancer; state only in Postgres, Redis and object storage, so API instances can be added freely.", "architecture"],
  ["2", "Back-of-the-envelope estimation", "Sizing the hashing budget: one argon2 verify is ~70 ms of CPU, so a worker handles roughly 14 logins per second per hashing slot.", "security"],
  ["4", "Rate limiter", "Sliding-window counter in Redis (two counters per client), plus adaptive login protection on top.", "security"],
  ["7", "Unique ID generator", "UUIDv7 primary keys: globally unique without coordination and time-ordered, so indexes stay compact.", "api"],
  ["10", "Notification system", "Email and push sent from outbox events, with per-user preferences, retries and suppression of bounced addresses.", "notifications"],
  ["16", "Proximity service", "PostGIS radius search, cached per geohash cell so nearby users share cache entries.", "search"],
  ["19", "Distributed message queue", "Transactional outbox table claimed with SELECT … FOR UPDATE SKIP LOCKED; at-least-once delivery with idempotent handlers.", "notifications"],
  ["20", "Metrics, monitoring and alerting", "Prometheus pull model: request rate, latency histograms, outbox backlog and login-protection counters.", "reliability"],
  ["22", "Hotel reservation system", "The closest match to parking: overlapping reservations prevented by the database, idempotent booking requests.", "booking"],
  ["24", "S3-like object storage", "Presigned direct uploads: the API never proxies image bytes; it verifies size and type afterwards.", "mobile"],
  ["26", "Payment system", "Payment orders, signed webhooks, de-duplication and a reconciliation job against the gateway.", "payments"],
  ["27", "Digital wallet", "Double-entry ledger: every money movement is a balanced transaction, enforced by a database trigger.", "payments"],
];

export default function SystemDesignNotes() {
  return (
    <>
      <DocHeader
        eyebrow="Start here"
        title="System design notes"
        lead="We studied the classic system design problems while building Parkezy. This page maps each idea we used to the part of the product where it lives, so you can jump from the concept to the real implementation."
      />

      <H2 id="map">Concepts and where we used them</H2>
      <DataTable
        head={["Ch.", "Concept", "How Parkezy applies it", "Read"]}
        rows={CHAPTERS.map(([ch, concept, how, slug]) => [
          <span key="c" className="font-mono text-[#6E5BC4]">{ch}</span>,
          <b key="t" className="text-[#1C1924]">{concept}</b>,
          how,
          <Link key="l" href={`/docs/${slug}`} className="font-semibold text-[#6E5BC4] hover:underline">
            {slug}
          </Link>,
        ])}
      />

      <H2 id="estimation">A worked estimate: how many logins can we take?</H2>
      <P>
        Password hashing is deliberately slow, which makes login the most expensive endpoint we have. The estimate below
        is the kind of reasoning from chapter 2, checked against what our load test measured.
      </P>
      <DataTable
        head={["Quantity", "Value", "Source"]}
        rows={[
          ["CPU per argon2id verify", "≈ 68 ms", "measured on our dev machine (p50)"],
          ["Hashes running at once per worker", "2", "PASSWORD_HASH_CONCURRENCY, bounds memory to 2 × 64 MiB"],
          ["Ceiling per worker", "≈ 2 / 0.068 ≈ 29 logins/s", "arithmetic"],
          ["Measured before hashing moved off the event loop", "23 logins/s (4 workers)", "k6 load test: hashing blocked everything else"],
        ]}
      />
      <Callout title="What the estimate told us" tone="success">
        The measured number was far below what 4 workers should manage, which pointed straight at the cause: hashing
        ran on the event loop and stalled every other request on that worker. It now runs in a bounded thread pool, and
        abusive login traffic is rejected before hashing (see Security).
      </Callout>

      <H2 id="credits">Credits</H2>
      <P>
        Chapter numbers refer to <i>System Design Interview: An Insider&apos;s Guide</i>, volumes 1 and 2, by Alex Xu
        (and Sahn Lam for volume 2). Our study notes follow those books; the designs on these pages are our own
        implementations of the ideas.
      </P>

      <PrevNext slug="system-design" />
    </>
  );
}
