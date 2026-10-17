import type { Metadata } from "next";
import Link from "next/link";
import { Download } from "lucide-react";

import { DocsMobileNav, DocsSidebar } from "@/components/docs/Sidebar";

export const metadata: Metadata = {
  title: { default: "Parkezy Docs — System Design", template: "%s · Parkezy Docs" },
  description:
    "How Parkezy works: architecture, booking engine, proximity search, payments and ledger, QR access, outbox, security and load-test results.",
};

export default function DocsLayout({ children }: LayoutProps<"/docs">) {
  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-40 border-b border-[#ECE9F5] bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="font-heading text-xl font-black tracking-tight text-[#1C1924] hover:text-[#6E5BC4]">
              Parkezy
            </Link>
            <span className="h-5 w-px bg-[#ECE9F5]" />
            <Link href="/docs" className="text-sm font-semibold text-[#6E5BC4]">
              Docs
            </Link>
          </div>
          <Link
            href="/download/android"
            className="inline-flex items-center gap-1.5 rounded-full bg-[#1C1924] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#6E5BC4] sm:text-sm"
          >
            <Download size={14} aria-hidden /> Get the app
          </Link>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-10 px-4 pt-8 sm:px-6 lg:grid-cols-[230px_minmax(0,1fr)] lg:pt-10">
        <DocsSidebar />
        <main className="min-w-0 pb-24">
          <DocsMobileNav />
          <article className="max-w-4xl">{children}</article>
        </main>
      </div>
    </div>
  );
}
