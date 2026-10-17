import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { ArchitectureDiagram } from "@/components/docs/diagrams";
import { DOCS, docHref } from "@/components/docs/nav";
import { Callout, DocHeader, Figure, H2, P, PrevNext, Stats } from "@/components/docs/ui";

export const metadata = { title: "Overview" };

export default function DocsHome() {
  return (
    <>
      <DocHeader
        eyebrow="Parkezy docs"
        title="How Parkezy works"
        lead={
          <>
            Parkezy is a parking marketplace: drivers find and book a spot, hosts earn from driveways and garages, and
            the gate opens with a QR code or a PIN. These pages explain the system behind it, section by section, with
            the real code, diagrams and the numbers from our tests.
          </>
        }
      />

      <Stats
        items={[
          { value: "89", label: "API routes in one stateless FastAPI service" },
          { value: "282", label: "automated backend tests on real Postgres + Redis" },
          { value: "69,424", label: "load-test requests, 0 wrong answers, 0 server errors" },
          { value: "1 of 100", label: "drivers wins when 100 book the same slot at once" },
        ]}
      />

      <H2 id="big-picture">The big picture</H2>
      <P>
        Every phone and browser talks to one API over HTTPS. The API keeps no state of its own: anything that must
        survive goes to PostgreSQL (the source of truth), anything short-lived goes to Redis, and photos go straight from
        the phone to object storage. Work that can happen later, such as emails, push notifications, expiring unpaid
        holds and checking payments, runs in a background worker that reads from a transactional outbox.
      </P>
      <Figure caption="Clients reach a single stateless API. Postgres is the source of truth; Redis holds caches, rate-limit counters, one-time tokens and the job queue; workers deliver everything asynchronous.">
        <ArchitectureDiagram />
      </Figure>

      <H2 id="principles">Design principles</H2>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {[
          ["The database enforces the rules that matter", "Double booking and unbalanced money are impossible at the Postgres level, not just checked in Python."],
          ["Every retry is safe", "Bookings take an Idempotency-Key, webhooks are de-duplicated, and every background handler can run twice without harm."],
          ["The server decides prices", "The app shows what the API quotes; amounts are recomputed server-side with Decimal arithmetic, never trusted from the client."],
          ["Fail fast, degrade gracefully", "Short timeouts return a clear 503 instead of hanging; if Redis is down, logins and bookings still work."],
        ].map(([t, d]) => (
          <div key={t} className="rounded-2xl border border-[#ECE9F5] p-5">
            <p className="font-semibold text-[#1C1924]">{t}</p>
            <p className="mt-2 text-sm leading-6 text-[#3F3A4B]">{d}</p>
          </div>
        ))}
      </div>

      <H2 id="sections">Read by section</H2>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {DOCS.filter((d) => d.slug).map((d) => (
          <Link key={d.slug} href={docHref(d.slug)} className="group rounded-2xl border border-[#ECE9F5] p-5 transition-colors hover:border-[#6E5BC4] hover:bg-[#FCFBFE]">
            <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#9A94AD]">{d.group}</p>
            <p className="mt-1 flex items-center gap-1 font-semibold text-[#1C1924] group-hover:text-[#6E5BC4]">
              {d.title} <ArrowRight size={15} className="opacity-0 transition-opacity group-hover:opacity-100" />
            </p>
            <p className="mt-1 text-sm leading-6 text-[#666173]">{d.summary}</p>
          </Link>
        ))}
      </div>

      <Callout title="Where the numbers come from">
        Test counts come from the backend test suite, and the capacity and failure figures from our k6 load and
        chaos tests (local machine, 4 API workers, October 2026). They show how the system behaves and where it
        breaks, not a promise of production throughput.
      </Callout>

      <PrevNext slug="" />
    </>
  );
}
