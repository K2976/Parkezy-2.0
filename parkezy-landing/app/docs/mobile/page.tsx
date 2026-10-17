import PhoneFrame from "@/components/PhoneFrame";
import PhoneScreenAccess from "@/components/PhoneScreenAccess";
import PhoneScreenBooking from "@/components/PhoneScreenBooking";
import PhoneScreenExplore from "@/components/PhoneScreenExplore";
import PhoneScreenHost from "@/components/PhoneScreenHost";
import { Sequence } from "@/components/docs/diagrams";
import { Callout, Code, CodeBlock, DataTable, DocHeader, Figure, H2, List, P, PrevNext } from "@/components/docs/ui";

export const metadata = { title: "Mobile app & interfaces" };

const SCREENS = [
  { title: "Explore", detail: "Map and list of nearby spots with price, distance and free slots", screen: <PhoneScreenExplore /> },
  { title: "Book", detail: "Server-quoted price breakdown, then pay or pay at the venue", screen: <PhoneScreenBooking /> },
  { title: "Access pass", detail: "Live QR code that refreshes itself, plus the offline PIN", screen: <PhoneScreenAccess /> },
  { title: "Host", detail: "Earnings, requests to approve and the gate scanner", screen: <PhoneScreenHost /> },
];

export default function Mobile() {
  return (
    <>
      <DocHeader
        eyebrow="Clients"
        title="Mobile app & interfaces"
        lead="One Expo React Native codebase for Android and iOS. Drivers and hosts use the same app; host features appear once an account becomes a host."
      />

      <H2 id="interfaces">Interfaces</H2>
      <P>The four core screens, recreated in HTML for the web (the same previews as on our home page).</P>
      <div className="mt-8 grid grid-cols-2 gap-x-4 gap-y-8 lg:grid-cols-4">
        {SCREENS.map((s) => (
          <figure key={s.title} className="text-center">
            <PhoneFrame activeScreen={0} className="mx-auto w-full max-w-[220px]">
              {[s.screen]}
            </PhoneFrame>
            <figcaption className="mt-3">
              <p className="font-semibold text-[#1C1924]">{s.title}</p>
              <p className="mt-1 text-xs leading-5 text-[#666173]">{s.detail}</p>
            </figcaption>
          </figure>
        ))}
      </div>

      <H2 id="screens">Screen map</H2>
      <P>Routes are files (Expo Router). Groups in parentheses share a layout without adding to the URL.</P>
      <CodeBlock
        lang="text"
        title="mobile/src/app"
        code={`(auth)/                 sign-in · sign-up · forgot-password      # email + password, or Google via Clerk
(app)/(tabs)/           index (explore) · bookings · host · account
(app)/listing/[id]      listing detail, reviews, book
(app)/booking/[id]      booking detail, payment, live QR pass, extend, check-out
(app)/report/[id]       dispute with photos
(app)/host/             new-listing · listing/[id] · bookings · scan (camera)
(app)/account/          profile · password · delete
(app)/notifications     in-app inbox
legal/[doc] · support · verify-email · sso-callback`}
      />

      <H2 id="data">Talking to the API</H2>
      <DataTable
        head={["Concern", "How the app handles it"]}
        rows={[
          ["Server state", "TanStack Query caches responses, refetches live screens (the booking screen every 20 s while a session is active)"],
          ["Auth", "Access token in memory only; refresh token in the Keychain / Keystore (SecureStore)"],
          ["Expired token", "On a 401 the client refreshes once (concurrent requests share one refresh) and retries"],
          ["Errors", "Every API error has the same JSON shape, so screens show the server's message and field errors"],
          ["Slow starts", "60 s request timeout: the hosted API sleeps when idle and can take ~55 s to wake"],
          ["Rules", "Prices, GST and booking limits come from GET /v1/config, never hard-coded in the app"],
          ["Device", "A random per-install id sent only when signing in, so a known phone gets less friction"],
        ]}
      />
      <CodeBlock
        lang="ts"
        title="mobile/src/api/client.ts"
        code={`/** Concurrent 401s share one refresh call. */
private refreshOnce(): Promise<string | null> {
  if (!this.tokens) return Promise.resolve(null);
  this.refreshing ??= this.tokens.refresh().finally(() => {
    this.refreshing = null;
  });
  return this.refreshing;
}`}
      />

      <H2 id="uploads">Photo uploads go straight to storage</H2>
      <Figure caption="The API never handles image bytes. It hands out a short-lived presigned URL, then verifies the stored object's size and type before a listing may use it.">
        <Sequence
          id="upload"
          title="Presigned upload sequence"
          actors={["Host app", "Parkezy API", "Backblaze B2"]}
          steps={[
            { from: 0, to: 1, label: "POST /v1/uploads (type, purpose)" },
            { from: 1, to: 0, label: "presigned PUT URL (15 min)", reply: true },
            { from: 0, to: 2, label: "PUT image bytes" },
            { from: 0, to: 1, label: "POST /uploads/{id}/complete" },
            { from: 1, to: 2, label: "HEAD: check size + type" },
            { from: 1, to: 0, label: "ready to attach to a listing", reply: true },
          ]}
        />
      </Figure>

      <H2 id="build">Builds and quality checks</H2>
      <List
        items={[
          <>Android APKs are built on EAS; API keys live in EAS environment variables, not in the repository.</>,
          <>Every change passes <Code>tsc --noEmit</Code> (strict TypeScript), ESLint and <Code>expo-doctor</Code> (21/21 checks).</>,
          <>Payments use the native Razorpay SDK, so they need the real app build; in Expo Go the app explains this instead of crashing.</>,
        ]}
      />
      <Callout title="Get the app">
        The latest Android build is on the <a href="/download/android" className="font-semibold text-[#6E5BC4] hover:underline">download page</a>.
      </Callout>

      <PrevNext slug="mobile" />
    </>
  );
}
