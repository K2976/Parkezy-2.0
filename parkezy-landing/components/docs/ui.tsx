import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowLeft, ArrowRight, Info, TriangleAlert, CircleCheck } from "lucide-react";

import { docHref, neighbours } from "./nav";

export function DocHeader({ eyebrow, title, lead }: { eyebrow: string; title: string; lead: ReactNode }) {
  return (
    <header className="mb-10 border-b border-[#ECE9F5] pb-8">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#6E5BC4]">{eyebrow}</p>
      <h1 className="mt-3 font-heading text-3xl font-black tracking-tight text-[#1C1924] sm:text-4xl">{title}</h1>
      <p className="mt-4 max-w-3xl text-[17px] leading-relaxed text-[#666173]">{lead}</p>
    </header>
  );
}

export function H2({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="group mt-14 scroll-mt-24 font-heading text-2xl font-extrabold tracking-tight text-[#1C1924]">
      <a href={`#${id}`} className="no-underline">
        {children}
        <span className="ml-2 text-[#6E5BC4] opacity-0 transition-opacity group-hover:opacity-100">#</span>
      </a>
    </h2>
  );
}

export function H3({ children }: { children: ReactNode }) {
  return <h3 className="mt-8 text-lg font-bold text-[#1C1924]">{children}</h3>;
}

export function P({ children }: { children: ReactNode }) {
  return <p className="mt-4 max-w-3xl leading-7 text-[#3F3A4B]">{children}</p>;
}

export function List({ items }: { items: ReactNode[] }) {
  return (
    <ul className="mt-4 max-w-3xl space-y-2 text-[#3F3A4B]">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 leading-7">
          <span className="mt-[11px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#6E5BC4]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded-md border border-[#ECE9F5] bg-[#F6F4FB] px-1.5 py-0.5 font-mono text-[0.85em] text-[#4B3D99]">
      {children}
    </code>
  );
}

const TONES = {
  info: { icon: Info, box: "border-[#D9D2F5] bg-[#F7F5FD]", title: "text-[#4B3D99]" },
  warn: { icon: TriangleAlert, box: "border-amber-200 bg-amber-50", title: "text-amber-800" },
  success: { icon: CircleCheck, box: "border-emerald-200 bg-emerald-50", title: "text-emerald-800" },
} as const;

export function Callout({ tone = "info", title, children }: { tone?: keyof typeof TONES; title: string; children: ReactNode }) {
  const t = TONES[tone];
  const Icon = t.icon;
  return (
    <aside className={`mt-6 max-w-3xl rounded-xl border p-4 ${t.box}`}>
      <p className={`flex items-center gap-2 text-sm font-bold ${t.title}`}>
        <Icon size={16} aria-hidden /> {title}
      </p>
      <div className="mt-1.5 text-[15px] leading-6 text-[#3F3A4B]">{children}</div>
    </aside>
  );
}

export function Stats({ items }: { items: { value: string; label: string }[] }) {
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((s) => (
        <div key={s.label} className="rounded-2xl border border-[#ECE9F5] bg-white p-4">
          <p className="font-heading text-2xl font-black text-[#1C1924] sm:text-3xl">{s.value}</p>
          <p className="mt-1 text-sm leading-5 text-[#666173]">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

export function DataTable({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="mt-6 overflow-x-auto rounded-xl border border-[#ECE9F5]">
      <table className="w-full min-w-[560px] border-collapse text-left text-sm">
        <thead className="bg-[#FAF9FD] text-[#1C1924]">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-[#ECE9F5] align-top">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 leading-6 text-[#3F3A4B]">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** `wide`: the content has a minimum width (SVG diagrams) and scrolls sideways on phones. */
export function Figure({ caption, children, wide = true }: { caption: ReactNode; children: ReactNode; wide?: boolean }) {
  return (
    <figure className="mt-8">
      <div className="overflow-x-auto rounded-2xl border border-[#ECE9F5] bg-[#FCFBFE] p-4 sm:p-6">{children}</div>
      {wide && <p className="mt-2 text-xs text-[#9A94AD] sm:hidden">Swipe sideways to see the whole figure.</p>}
      <figcaption className="mt-3 text-sm leading-6 text-[#666173]">{caption}</figcaption>
    </figure>
  );
}

// ---------------------------------------------------------------- code blocks

const KEYWORDS: Record<string, string[]> = {
  python: ["def", "async", "await", "return", "if", "else", "elif", "for", "in", "not", "and", "or", "class", "try", "except", "raise", "with", "import", "from", "None", "True", "False", "is", "lambda"],
  sql: ["CREATE", "TABLE", "CONSTRAINT", "EXCLUDE", "USING", "WITH", "WHERE", "SELECT", "FROM", "FOR", "UPDATE", "SKIP", "LOCKED", "IF", "THEN", "END", "BEGIN", "RETURN", "RETURNS", "FUNCTION", "TRIGGER", "AFTER", "INSERT", "ON", "EACH", "ROW", "EXECUTE", "DEFERRABLE", "INITIALLY", "DEFERRED", "RAISE", "EXCEPTION", "ORDER", "BY", "LIMIT", "AND", "IN", "NULL", "NOT", "AS", "LANGUAGE", "CREATE", "UNIQUE"],
  ts: ["const", "let", "async", "await", "return", "if", "else", "export", "function", "import", "from", "new", "type", "interface", "throw", "try", "catch"],
  http: ["GET", "POST", "PUT", "PATCH", "DELETE", "HTTP/1.1"],
  json: [],
  text: [],
};

function highlight(line: string, lang: string): ReactNode {
  const comment = lang === "sql" ? "--" : lang === "python" || lang === "text" ? "#" : "//";
  const at = line.indexOf(comment);
  const body = at >= 0 ? line.slice(0, at) : line;
  const tail = at >= 0 ? line.slice(at) : "";
  const words = new Set(KEYWORDS[lang] ?? []);
  const parts = body.split(/("[^"]*"|'[^']*'|\b\d[\d_.]*\b|\b[A-Za-z_]+\b)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (!part) return null;
        if (/^["']/.test(part)) return <span key={i} className="text-[#A5E3B5]">{part}</span>;
        if (/^\d/.test(part)) return <span key={i} className="text-[#F5C38B]">{part}</span>;
        if (words.has(part)) return <span key={i} className="text-[#C4B5FD]">{part}</span>;
        return <span key={i}>{part}</span>;
      })}
      {tail && <span className="text-[#8B85A0]">{tail}</span>}
    </>
  );
}

export function CodeBlock({ code, lang = "text", title }: { code: string; lang?: keyof typeof KEYWORDS; title?: string }) {
  const lines = code.replace(/\n$/, "").split("\n");
  return (
    <div className="mt-6 overflow-hidden rounded-xl border border-[#2A2638] bg-[#17141F] shadow-sm">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
        <span className="truncate font-mono text-xs text-[#B9B3CC]">{title ?? lang}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#8B85A0]">{lang}</span>
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] leading-6 text-[#EDEAF5]">
        <code>
          {lines.map((line, i) => (
            <div key={i} className="min-h-6 whitespace-pre">
              {highlight(line, lang)}
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}

export function PrevNext({ slug }: { slug: string }) {
  const { prev, next } = neighbours(slug);
  return (
    <nav className="mt-16 grid gap-3 border-t border-[#ECE9F5] pt-8 sm:grid-cols-2" aria-label="Previous and next">
      {prev ? (
        <Link href={docHref(prev.slug)} className="group rounded-xl border border-[#ECE9F5] p-4 hover:border-[#6E5BC4]">
          <span className="flex items-center gap-1 text-xs text-[#666173]"><ArrowLeft size={14} /> Previous</span>
          <span className="mt-1 block font-semibold text-[#1C1924] group-hover:text-[#6E5BC4]">{prev.title}</span>
        </Link>
      ) : (
        <span />
      )}
      {next && (
        <Link href={docHref(next.slug)} className="group rounded-xl border border-[#ECE9F5] p-4 text-right hover:border-[#6E5BC4]">
          <span className="flex items-center justify-end gap-1 text-xs text-[#666173]">Next <ArrowRight size={14} /></span>
          <span className="mt-1 block font-semibold text-[#1C1924] group-hover:text-[#6E5BC4]">{next.title}</span>
        </Link>
      )}
    </nav>
  );
}
