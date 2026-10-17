const ACCENT = "#6E5BC4";
const MUTED = "#666173";
const GRID = "#ECE9F5";
const FONT = { fontFamily: "var(--font-sans), system-ui, sans-serif" };

export type Bar = { label: string; value: number; display?: string; tone?: "accent" | "muted" | "success" | "danger" };

const BAR_TONE = { accent: "bg-[#6E5BC4]", muted: "bg-[#C9C1E8]", success: "bg-emerald-500", danger: "bg-rose-400" };

/** Horizontal bars, plain HTML so labels wrap nicely on phones. */
export function BarChart({ bars, unit, title }: { bars: Bar[]; unit: string; title: string }) {
  const max = Math.max(...bars.map((b) => b.value));
  return (
    <div role="img" aria-label={title} className="mx-auto max-w-3xl space-y-3">
      {bars.map((b) => (
        <div key={b.label} className="grid grid-cols-[minmax(0,10.5rem)_1fr] items-center gap-3 sm:grid-cols-[13rem_1fr]">
          <span className="truncate font-mono text-xs text-[#3F3A4B] sm:text-[13px]" title={b.label}>
            {b.label}
          </span>
          <div className="flex items-center gap-2">
            <div className="h-6 flex-1 rounded-md bg-[#F4F2F8]">
              <div
                className={`h-6 rounded-md ${BAR_TONE[b.tone ?? "accent"]}`}
                style={{ width: `${Math.max(1.5, (b.value / max) * 100)}%` }}
              />
            </div>
            <span className="w-24 shrink-0 text-right text-sm font-semibold tabular-nums text-[#1C1924]">
              {b.display ?? b.value.toLocaleString("en-IN")} <span className="font-normal text-[#666173]">{unit}</span>
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export type Series = { name: string; color: string; points: [number, number][]; dashed?: boolean; area?: [number, number][] };

/** Small SVG line chart with axes, gridlines and an optional shaded band per series. */
export function LineChart({
  series,
  xLabel,
  yLabel,
  title,
  xTicks,
  yTicks,
  yFormat = (v: number) => String(v),
}: {
  series: Series[];
  xLabel: string;
  yLabel: string;
  title: string;
  xTicks: number[];
  yTicks: number[];
  yFormat?: (v: number) => string;
}) {
  const W = 720;
  const H = 320;
  const m = { l: 64, r: 20, t: 20, b: 52 };
  const xMax = Math.max(...xTicks);
  const yMax = Math.max(...yTicks);
  const sx = (x: number) => m.l + (x / xMax) * (W - m.l - m.r);
  const sy = (y: number) => H - m.b - (y / yMax) * (H - m.t - m.b);
  const path = (pts: [number, number][]) => pts.map(([x, y], i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="mx-auto block w-full" style={{ minWidth: 520, ...FONT }}>
        <title>{title}</title>
        {yTicks.map((t) => (
          <g key={`y${t}`}>
            <line x1={m.l} x2={W - m.r} y1={sy(t)} y2={sy(t)} stroke={GRID} />
            <text x={m.l - 10} y={sy(t) + 4} fontSize={11} fill={MUTED} textAnchor="end">
              {yFormat(t)}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={`x${t}`} x={sx(t)} y={H - m.b + 18} fontSize={11} fill={MUTED} textAnchor="middle">
            {t}
          </text>
        ))}
        <line x1={m.l} x2={W - m.r} y1={H - m.b} y2={H - m.b} stroke="#C9C3D9" />
        <text x={(m.l + W - m.r) / 2} y={H - 10} fontSize={12} fill={MUTED} textAnchor="middle">
          {xLabel}
        </text>
        <text x={16} y={(m.t + H - m.b) / 2} fontSize={12} fill={MUTED} textAnchor="middle" transform={`rotate(-90 16 ${(m.t + H - m.b) / 2})`}>
          {yLabel}
        </text>
        {series.map((s) => (
          <g key={s.name}>
            {s.area && <path d={`${path(s.points)} ${path([...s.area].reverse()).replace("M", "L")} Z`} fill={s.color} opacity={0.12} />}
            <path d={path(s.points)} fill="none" stroke={s.color} strokeWidth={2.2} strokeDasharray={s.dashed ? "6 5" : undefined} />
          </g>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap justify-center gap-4 text-xs text-[#666173]">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-5" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** One wide bar split into parts, e.g. 1 booking succeeded vs 99 rejected. */
export function SplitBar({ parts, title }: { parts: { label: string; value: number; color: string }[]; title: string }) {
  const total = parts.reduce((a, p) => a + p.value, 0);
  return (
    <div role="img" aria-label={title} className="mx-auto max-w-3xl">
      <div className="flex h-10 overflow-hidden rounded-lg">
        {parts.map((p) => (
          <div key={p.label} style={{ width: `${(p.value / total) * 100}%`, background: p.color, minWidth: 6 }} title={`${p.label}: ${p.value}`} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-[#3F3A4B]">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: p.color }} />
            <b className="tabular-nums">{p.value}</b> {p.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export { ACCENT };
