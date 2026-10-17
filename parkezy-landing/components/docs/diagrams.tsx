import type { ReactNode } from "react";
import { ArrowDown } from "lucide-react";

const INK = "#1C1924";
const MUTED = "#666173";
const ACCENT = "#6E5BC4";
const LINE = "#B8B0D6";

const FONT = { fontFamily: "var(--font-sans), system-ui, sans-serif" };

function Marker({ id, color = ACCENT }: { id: string; color?: string }) {
  return (
    <defs>
      <marker id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill={color} />
      </marker>
    </defs>
  );
}

// ---------------------------------------------------------------- sequence diagram

export type SeqStep =
  | { from: number; to: number; label: string; reply?: boolean }
  | { note: string; over: [number, number] };

export function Sequence({ id, actors, steps, title }: { id: string; actors: string[]; steps: SeqStep[]; title: string }) {
  const colW = 176;
  const pad = 16;
  const width = pad * 2 + actors.length * colW;
  const cx = (i: number) => pad + colW * i + colW / 2;
  const top = 64;
  const rowH = 44;
  const height = top + steps.length * rowH + 28;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title} className="mx-auto block w-full" style={{ minWidth: Math.min(width, 640), ...FONT }}>
      <title>{title}</title>
      <Marker id={`${id}-a`} />
      <Marker id={`${id}-r`} color={MUTED} />
      {actors.map((a, i) => (
        <g key={a}>
          <line x1={cx(i)} y1={48} x2={cx(i)} y2={height - 8} stroke={LINE} strokeDasharray="4 5" />
          <rect x={cx(i) - colW / 2 + 10} y={8} width={colW - 20} height={40} rx={10} fill="#fff" stroke={ACCENT} strokeWidth={1.5} />
          <text x={cx(i)} y={33} textAnchor="middle" fontSize={13} fontWeight={700} fill={INK}>
            {a}
          </text>
        </g>
      ))}
      {steps.map((s, i) => {
        const y = top + i * rowH + 22;
        if ("note" in s) {
          const [a, b] = s.over;
          // Span the given lifelines, widened to fit the text (about 6.6 px per character at 12 px).
          const centre = (cx(Math.min(a, b)) + cx(Math.max(a, b))) / 2;
          const half = Math.max((cx(Math.max(a, b)) - cx(Math.min(a, b))) / 2 + colW / 2 - 18, (s.note.length * 6.6) / 2 + 14);
          const x1 = Math.max(4, centre - half);
          const x2 = Math.min(width - 4, centre + half);
          return (
            <g key={i}>
              <rect x={x1} y={y - 15} width={x2 - x1} height={30} rx={8} fill="#FFF7E6" stroke="#F0D9A8" />
              <text x={(x1 + x2) / 2} y={y + 4} textAnchor="middle" fontSize={12} fill="#7A5A12">
                {s.note}
              </text>
            </g>
          );
        }
        const color = s.reply ? MUTED : ACCENT;
        if (s.from === s.to) {
          const x = cx(s.from);
          return (
            <g key={i}>
              <path d={`M${x},${y - 8} h34 v16 h-30`} fill="none" stroke={color} strokeWidth={1.5} markerEnd={`url(#${id}-${s.reply ? "r" : "a"})`} />
              <text x={x + 42} y={y + 4} fontSize={12} fill={INK}>
                {s.label}
              </text>
            </g>
          );
        }
        const x1 = cx(s.from);
        const x2 = cx(s.to);
        const dir = x2 > x1 ? 1 : -1;
        return (
          <g key={i}>
            <line
              x1={x1 + dir * 4}
              y1={y}
              x2={x2 - dir * 6}
              y2={y}
              stroke={color}
              strokeWidth={1.5}
              strokeDasharray={s.reply ? "5 4" : undefined}
              markerEnd={`url(#${id}-${s.reply ? "r" : "a"})`}
            />
            <text x={(x1 + x2) / 2} y={y - 7} textAnchor="middle" fontSize={12} fill={s.reply ? MUTED : INK}>
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------- vertical flowchart

type Tone = "default" | "accent" | "success" | "warn" | "danger";
export type FlowStep = { title: string; detail?: ReactNode; tone?: Tone; tag?: string };

const TONE_CLASS: Record<Tone, string> = {
  default: "border-[#ECE9F5] bg-white",
  accent: "border-[#CFC6F2] bg-[#F7F5FD]",
  success: "border-emerald-200 bg-emerald-50",
  warn: "border-amber-200 bg-amber-50",
  danger: "border-rose-200 bg-rose-50",
};

function FlowCard({ step }: { step: FlowStep }) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${TONE_CLASS[step.tone ?? "default"]}`}>
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-semibold text-[#1C1924]">{step.title}</p>
        {step.tag && (
          <span className="rounded-full bg-white/80 px-2 py-0.5 font-mono text-[11px] text-[#6E5BC4] ring-1 ring-[#E3DDF7]">{step.tag}</span>
        )}
      </div>
      {step.detail && <div className="mt-1 text-sm leading-6 text-[#3F3A4B]">{step.detail}</div>}
    </div>
  );
}

export function Flow({ steps }: { steps: (FlowStep | { branches: FlowStep[] })[] }) {
  return (
    <div className="mx-auto max-w-3xl">
      {steps.map((s, i) => (
        <div key={i}>
          {i > 0 && (
            <div className="flex justify-center py-1.5 text-[#B8B0D6]" aria-hidden>
              <ArrowDown size={18} />
            </div>
          )}
          {"branches" in s ? (
            <div className={`grid gap-3 ${s.branches.length > 2 ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
              {s.branches.map((b) => (
                <FlowCard key={b.title} step={b} />
              ))}
            </div>
          ) : (
            <FlowCard step={s} />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- architecture

type BoxProps = { x: number; y: number; w: number; h: number; title: string; sub?: string; fill?: string; stroke?: string };

function Box({ x, y, w, h, title, sub, fill = "#fff", stroke = ACCENT }: BoxProps) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={12} fill={fill} stroke={stroke} strokeWidth={1.5} />
      <text x={x + w / 2} y={y + (sub ? h / 2 - 3 : h / 2 + 5)} textAnchor="middle" fontSize={14} fontWeight={700} fill={INK}>
        {title}
      </text>
      {sub && (
        <text x={x + w / 2} y={y + h / 2 + 15} textAnchor="middle" fontSize={11.5} fill={MUTED}>
          {sub}
        </text>
      )}
    </g>
  );
}

function Arrow({ id, d, label, lx, ly, dashed }: { id: string; d: string; label?: string; lx?: number; ly?: number; dashed?: boolean }) {
  return (
    <g>
      <path d={d} fill="none" stroke={dashed ? MUTED : ACCENT} strokeWidth={1.5} strokeDasharray={dashed ? "5 4" : undefined} markerEnd={`url(#${id})`} />
      {label && (
        <text x={lx} y={ly} fontSize={11.5} fill={MUTED} textAnchor="middle">
          {label}
        </text>
      )}
    </g>
  );
}

export function ArchitectureDiagram() {
  const id = "arch-a";
  const tier = (y: number, label: string) => (
    <text x={14} y={y} fontSize={11} fontWeight={700} fill={ACCENT} letterSpacing={1.2}>
      {label}
    </text>
  );
  return (
    <svg viewBox="0 0 980 640" role="img" aria-label="Parkezy architecture" className="mx-auto block w-full" style={{ minWidth: 720, ...FONT }}>
      <title>Parkezy architecture</title>
      <defs>
        <marker id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill={ACCENT} />
        </marker>
      </defs>
      {tier(28, "CLIENTS")}
      <Box x={120} y={40} w={250} h={58} title="Mobile app" sub="Expo · React Native · Android / iOS" />
      <Box x={400} y={40} w={230} h={58} title="Landing site" sub="Next.js on Vercel" />
      <Box x={660} y={40} w={220} h={58} title="Google sign-in" sub="Clerk (OIDC tokens)" fill="#FAF9FD" />

      {tier(140, "EDGE")}
      <Box x={120} y={152} w={760} h={44} title="Render edge · HTTPS · request size cap · security headers" />

      {tier(238, "API (STATELESS)")}
      <rect x={120} y={250} width={760} height={118} rx={14} fill="#F7F5FD" stroke={ACCENT} strokeWidth={1.5} />
      <text x={500} y={274} textAnchor="middle" fontSize={14} fontWeight={700} fill={INK}>
        FastAPI · 89 routes · Pydantic validation · rate limits
      </text>
      {["Auth", "Search", "Bookings", "Payments", "Access", "Host", "Admin"].map((m, i) => (
        <g key={m}>
          <rect x={140 + i * 104} y={292} width={92} height={32} rx={8} fill="#fff" stroke="#D9D2F5" />
          <text x={186 + i * 104} y={313} textAnchor="middle" fontSize={12.5} fill={INK}>
            {m}
          </text>
        </g>
      ))}
      <text x={500} y={352} textAnchor="middle" fontSize={11.5} fill={MUTED}>
        domain rules · pricing · booking state machine · ledger · outbox writer
      </text>

      {tier(410, "DATA")}
      <Box x={120} y={422} w={240} h={66} title="PostgreSQL + PostGIS" sub="Neon · source of truth" />
      <Box x={380} y={422} w={240} h={66} title="Redis" sub="cache · limits · one-time tokens · queue" />
      <Box x={640} y={422} w={240} h={66} title="Object storage" sub="Backblaze B2 (S3 API)" />

      {tier(530, "WORKERS & PROVIDERS")}
      <Box x={120} y={542} w={240} h={66} title="Celery worker + beat" sub="outbox · expiries · reconcile" fill="#FAF9FD" />
      <Box x={380} y={542} w={150} h={66} title="Razorpay" sub="payments" fill="#FAF9FD" />
      <Box x={545} y={542} w={150} h={66} title="Resend" sub="email" fill="#FAF9FD" />
      <Box x={710} y={542} w={170} h={66} title="Expo Push" sub="notifications" fill="#FAF9FD" />

      <Arrow id={id} d="M245,98 V150" />
      <Arrow id={id} d="M515,98 V150" />
      <Arrow id={id} d="M500,196 V248" />
      <Arrow id={id} d="M240,368 V420" />
      <Arrow id={id} d="M500,368 V420" />
      <Arrow id={id} d="M760,368 V420" label="presign" lx={796} ly={398} />
      <Arrow id={id} d="M245,40 V22 H950 V455 H884" dashed />
      <text x={600} y={16} fontSize={11.5} fill={MUTED} textAnchor="middle">
        photos go straight from the phone to storage (presigned PUT)
      </text>
      <Arrow id={id} d="M770,98 C 770,120 700,130 690,150" dashed />
      <Arrow id={id} d="M240,488 V540" label="claims events" lx={200} ly={518} />
      <Arrow id={id} d="M360,575 H378" />
      <path d="M300,608 V626 H795" fill="none" stroke={ACCENT} strokeWidth={1.5} />
      <Arrow id={id} d="M620,626 V610" />
      <Arrow id={id} d="M795,626 V610" />
      <Arrow id={id} d="M405,542 V516 H370 V370" label="webhooks" lx={430} ly={530} dashed />
    </svg>
  );
}

// ---------------------------------------------------------------- booking state machine

export function BookingStateMachine() {
  const id = "bsm-a";
  const W = 150;
  const H = 46;
  const node = (x: number, y: number, label: string, tone: "live" | "end" | "ok" = "live") => (
    <g>
      <rect
        x={x}
        y={y}
        width={W}
        height={H}
        rx={23}
        fill={tone === "end" ? "#F4F2F8" : tone === "ok" ? "#ECFDF5" : "#fff"}
        stroke={tone === "end" ? "#C9C3D9" : tone === "ok" ? "#34D399" : ACCENT}
        strokeWidth={1.5}
      />
      <text x={x + W / 2} y={y + 28} textAnchor="middle" fontSize={13} fontFamily="ui-monospace, monospace" fill={INK}>
        {label}
      </text>
    </g>
  );
  const cols = [70, 290, 510, 730, 950];
  const y = 96;
  const mid = y + H / 2;
  const edge = (a: number, b: number, label: string) => (
    <Arrow id={id} d={`M${cols[a] + W},${mid} H${cols[b] - 2}`} label={label} lx={(cols[a] + W + cols[b]) / 2} ly={mid - 10} />
  );
  const tick = (i: number) => cols[i] + W / 2;
  return (
    <svg viewBox="0 0 1120 330" role="img" aria-label="Booking state machine" className="mx-auto block w-full" style={{ minWidth: 760, ...FONT }}>
      <title>Booking state machine</title>
      <Marker id={id} />
      <circle cx={24} cy={mid} r={8} fill={INK} />
      <Arrow id={id} d={`M33,${mid} H${cols[0] - 2}`} />
      <text x={50} y={mid + 22} fontSize={11} fill={MUTED} textAnchor="middle">request</text>
      <Arrow id={id} d={`M24,${mid - 9} C 24,24 ${tick(1)},24 ${tick(1)},${y - 2}`} label="auto-accept" lx={tick(1) - 40} ly={30} />
      {node(cols[0], y, "pending_approval")}
      {node(cols[1], y, "pending_payment")}
      {node(cols[2], y, "confirmed")}
      {node(cols[3], y, "checked_in")}
      {node(cols[4], y, "completed", "ok")}
      {edge(0, 1, "approve")}
      {edge(1, 2, "paid")}
      {edge(2, 3, "check-in")}
      {edge(3, 4, "check-out")}

      {/* cancel / expire bus: any state before check-in */}
      <path
        d={`M${tick(0) + 30},${y + H} V200 M${tick(1)},${y + H} V200 M${tick(2)},${y + H} V200 M${tick(0) + 30},200 H${tick(2)}`}
        fill="none"
        stroke={MUTED}
        strokeWidth={1.5}
      />
      <text x={tick(2) + 12} y={204} fontSize={11.5} fill={MUTED}>cancel · expire (any time before check-in)</text>
      <Arrow id={id} d={`M${tick(1) - 60},200 V252`} dashed />
      <Arrow id={id} d={`M${tick(2) - 40},200 V252`} dashed />
      <Arrow id={id} d={`M${tick(0) - 30},${y + H} V252`} label="reject" lx={tick(0) - 52} ly={228} dashed />
      {node(tick(0) - 30 - W / 2, 254, "rejected", "end")}
      {node(tick(1) - 60 - W / 2, 254, "cancelled", "end")}
      {node(tick(2) - 40 - W / 2, 254, "expired", "end")}
      <text x={730} y={276} fontSize={11.5} fill={MUTED}>pay-at-venue bookings skip</text>
      <text x={730} y={292} fontSize={11.5} fill={MUTED}>pending_payment entirely</text>
    </svg>
  );
}

// ---------------------------------------------------------------- geohash cells

export function GeohashGrid() {
  const cell = 90;
  const ox = 40;
  const oy = 30;
  const cols = 7;
  const rows = 4;
  const chosen = { c: 3, r: 1 };
  const ccx = ox + chosen.c * cell + cell / 2;
  const ccy = oy + chosen.r * cell + cell / 2;
  const userA = { x: ccx - 22, y: ccy + 12 };
  const userB = { x: ccx + 26, y: ccy - 20 };
  const radius = 70;
  const halfDiag = Math.hypot(cell / 2, cell / 2);
  return (
    <svg viewBox="0 0 720 436" role="img" aria-label="Geohash cell search" className="mx-auto block w-full" style={{ minWidth: 560, ...FONT }}>
      <title>Geohash cell search</title>
      {Array.from({ length: rows }).map((_, r) =>
        Array.from({ length: cols }).map((_, c) => (
          <rect
            key={`${r}-${c}`}
            x={ox + c * cell}
            y={oy + r * cell}
            width={cell}
            height={cell}
            fill={c === chosen.c && r === chosen.r ? "#EEEAFB" : "#fff"}
            stroke="#E3DEF2"
          />
        )),
      )}
      <circle cx={ccx} cy={ccy} r={radius + halfDiag} fill="none" stroke={ACCENT} strokeDasharray="6 5" strokeWidth={1.5} />
      <circle cx={userA.x} cy={userA.y} r={radius} fill="rgba(110,91,196,0.10)" stroke={ACCENT} strokeWidth={1.5} />
      <circle cx={userB.x} cy={userB.y} r={radius} fill="rgba(47,138,106,0.08)" stroke="#2F8A6A" strokeWidth={1.5} />
      {[
        [120, 70], [250, 210], [450, 150], [300, 100], [470, 230], [520, 90], [600, 300], [180, 300], [420, 300], [350, 250],
      ].map(([x, y], i) => (
        <rect key={i} x={x - 6} y={y - 6} width={12} height={12} rx={3} fill="#1C1924" opacity={0.75} />
      ))}
      <circle cx={userA.x} cy={userA.y} r={6} fill={ACCENT} />
      <circle cx={userB.x} cy={userB.y} r={6} fill="#2F8A6A" />
      <text x={userA.x - 10} y={userA.y + 24} fontSize={12} fill={INK} textAnchor="middle">driver A</text>
      <text x={userB.x + 12} y={userB.y - 12} fontSize={12} fill={INK}>driver B</text>
      <text x={ox + chosen.c * cell + 5} y={oy + chosen.r * cell + 14} fontSize={11} fill={ACCENT} fontWeight={700}>shared cell</text>
      <g transform="translate(40,410)">
        <rect width={12} height={12} rx={3} fill="#1C1924" opacity={0.75} />
        <text x={18} y={11} fontSize={12} fill={MUTED}>listing</text>
        <line x1={90} y1={6} x2={120} y2={6} stroke={ACCENT} strokeDasharray="6 5" strokeWidth={1.5} />
        <text x={126} y={11} fontSize={12} fill={MUTED}>one cached query for the cell</text>
        <circle cx={340} cy={6} r={6} fill="rgba(110,91,196,0.15)" stroke={ACCENT} />
        <text x={352} y={11} fontSize={12} fill={MUTED}>each driver&apos;s own radius</text>
      </g>
    </svg>
  );
}
