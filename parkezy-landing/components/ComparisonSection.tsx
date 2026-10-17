"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

export default function ComparisonSection() {
  return (
    <section id="features" className="py-24 bg-slate-50 border-y border-slate-200/80">
      <div className="max-w-7xl mx-auto px-6 md:px-8">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs font-bold text-[#6E5BC4] uppercase tracking-widest block mb-2">
            Why Drivers Choose Parkezy
          </span>
          <h2 className="text-3xl md:text-5xl font-black text-[#1C1924] tracking-tight leading-tight">
            Stop guessing. Start parking.
          </h2>
          <p className="text-base md:text-lg text-slate-600 mt-4">
            See how the traditional parking struggle compares to the effortless Parkezy experience.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto text-left">
          {/* Old Traditional Parking Card */}
          <div className="bg-white rounded-3xl p-8 border border-slate-200/80 shadow-sm relative overflow-hidden">
            <div className="flex items-center gap-2.5 mb-6 text-red-500 font-bold text-sm tracking-wide uppercase">
              <div className="w-8 h-8 rounded-xl bg-red-50 flex items-center justify-center">
                <X size={18} />
              </div>
              <span>Traditional Parking</span>
            </div>

            <ul className="space-y-4 text-slate-600 text-sm font-medium">
              <li className="flex items-start gap-3">
                <X size={17} className="text-red-500 shrink-0 mt-0.5" />
                <span>Circling congested blocks for 20–30 mins hoping for an empty space.</span>
              </li>
              <li className="flex items-start gap-3">
                <X size={17} className="text-red-500 shrink-0 mt-0.5" />
                <span>Arriving at a crowded lot only to find &ldquo;FULL&rdquo; signs.</span>
              </li>
              <li className="flex items-start gap-3">
                <X size={17} className="text-red-500 shrink-0 mt-0.5" />
                <span>Getting stuck at underground barriers with zero cellular signal.</span>
              </li>
              <li className="flex items-start gap-3">
                <X size={17} className="text-red-500 shrink-0 mt-0.5" />
                <span>Unregulated cash pricing and manual paper tickets that get lost.</span>
              </li>
              <li className="flex items-start gap-3">
                <X size={17} className="text-red-500 shrink-0 mt-0.5" />
                <span>No way to know if EV charging ports are functional or free.</span>
              </li>
            </ul>
          </div>

          {/* Parkezy Smart Solution Card */}
          <div className="bg-[#2E2A35] rounded-3xl p-8 border border-[#6E5BC4]/40 shadow-xl relative overflow-hidden text-white">
            <div className="absolute top-0 right-0 w-48 h-48 bg-[#6E5BC4]/15 rounded-full blur-2xl pointer-events-none" />

            <div className="mb-6 text-emerald-400 font-bold text-sm tracking-wide uppercase">
              <span>The Parkezy Experience</span>
            </div>

            <ul className="space-y-4 text-slate-200 text-sm font-medium">
              <li className="flex items-start gap-3">
                <Check size={17} className="text-emerald-400 shrink-0 mt-0.5 stroke-[3]" />
                <span><strong className="text-white">100% Guaranteed Space:</strong> Locked bay held for you before you drive.</span>
              </li>
              <li className="flex items-start gap-3">
                <Check size={17} className="text-emerald-400 shrink-0 mt-0.5 stroke-[3]" />
                <span><strong className="text-white">Live Google Maps Navigation:</strong> Direct turn-by-turn directions to your bay.</span>
              </li>
              <li className="flex items-start gap-3">
                <Check size={17} className="text-emerald-400 shrink-0 mt-0.5 stroke-[3]" />
                <span><strong className="text-white">Offline Gate PIN:</strong> Cryptographic 6-digit backup code works in any basement.</span>
              </li>
              <li className="flex items-start gap-3">
                <Check size={17} className="text-emerald-400 shrink-0 mt-0.5 stroke-[3]" />
                <span><strong className="text-white">Instant UPI & Tax Invoices:</strong> Automated GST receipt and 1-tap checkout.</span>
              </li>
              <li className="flex items-start gap-3">
                <Check size={17} className="text-emerald-400 shrink-0 mt-0.5 stroke-[3]" />
                <span><strong className="text-white">EV Supercharger Booking:</strong> Reserve dedicated charging ports in advance.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
