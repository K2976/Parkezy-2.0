"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { DOCS, docHref } from "./nav";

const GROUPS = [...new Set(DOCS.map((d) => d.group))];

function Links({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {GROUPS.map((group) => (
        <div key={group} className="mb-6">
          <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-[0.12em] text-[#9A94AD]">{group}</p>
          <ul className="space-y-0.5">
            {DOCS.filter((d) => d.group === group).map((d) => {
              const href = docHref(d.slug);
              const active = pathname === href;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={`block rounded-lg px-3 py-1.5 text-sm transition-colors ${
                      active ? "bg-[#F1EEFC] font-semibold text-[#4B3D99]" : "text-[#3F3A4B] hover:bg-[#F7F5FD] hover:text-[#1C1924]"
                    }`}
                  >
                    {d.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </>
  );
}

export function DocsSidebar() {
  return (
    <nav aria-label="Documentation" className="sticky top-20 hidden max-h-[calc(100vh-6rem)] overflow-y-auto pb-10 lg:block">
      <Links />
    </nav>
  );
}

export function DocsMobileNav() {
  const pathname = usePathname();
  const current = DOCS.find((d) => docHref(d.slug) === pathname);
  return (
    <details className="group mb-8 rounded-xl border border-[#ECE9F5] bg-white lg:hidden">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-[#1C1924]">
        <span>
          <span className="text-[#9A94AD]">Docs / </span>
          {current?.title ?? "Sections"}
        </span>
        <span className="text-[#6E5BC4] transition-transform group-open:rotate-180">▾</span>
      </summary>
      <div className="border-t border-[#ECE9F5] px-1 pt-4">
        <Links onNavigate={() => document.querySelector<HTMLDetailsElement>("details[open]")?.removeAttribute("open")} />
      </div>
    </details>
  );
}
