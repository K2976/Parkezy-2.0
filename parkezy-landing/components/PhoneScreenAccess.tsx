"use client";

import React from "react";
import { ArrowLeft, Clock, Navigation, CheckCircle2, QrCode } from "lucide-react";
import AppBackdrop from "./AppBackdrop";

export default function PhoneScreenAccess() {
  return (
    <AppBackdrop>
      {/* Status Bar */}
      <div className="pt-3 px-6 pb-1 flex items-center justify-between text-xs text-[#1C1924] font-bold">
        <span>9:41</span>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-2.5 border border-[#1C1924] rounded-sm p-0.5 flex items-center">
            <div className="w-full h-full bg-[#1C1924] rounded-[1px]" />
          </div>
        </div>
      </div>

      {/* Screen Header */}
      <div className="px-4 py-2 flex items-center justify-between border-b border-[rgba(215,210,230,0.5)]">
        <div className="flex items-center gap-2">
          <button className="w-8 h-8 rounded-full bg-[#FFFFFF] border border-[rgba(215,210,230,0.7)] flex items-center justify-center text-[#1C1924] shadow-xs">
            <ArrowLeft size={16} />
          </button>
          <span className="text-sm font-bold text-[#1C1924]">Active Pass</span>
        </div>
        <div className="bg-[#E3F2EC] text-[#2F8A6A] text-[10px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#2F8A6A]" /> Checked in
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 px-4 py-3 space-y-3 overflow-y-auto pb-10 text-left">
        {/* Real Session Ring Card (from mobile/src/ui/charts.tsx ProgressRing) */}
        <div className="bg-[rgba(255,255,255,0.85)] backdrop-blur-xl rounded-[24px] p-3.5 border border-[rgba(215,210,230,0.7)] shadow-[0_8px_20px_rgba(45,35,70,0.06)] flex items-center gap-4">
          {/* Circular Progress Gauge SVG */}
          <div className="relative w-20 h-20 shrink-0 flex items-center justify-center">
            <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="32" stroke="#F2F0F7" strokeWidth="8" fill="none" />
              <circle
                cx="40"
                cy="40"
                r="32"
                stroke="#6E5BC4"
                strokeWidth="8"
                fill="none"
                strokeDasharray="201"
                strokeDashoffset="65"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center leading-none">
              <span className="text-xs font-black text-[#1C1924]">1h 48m</span>
              <span className="text-[9px] text-[#666173] font-medium mt-0.5">left</span>
            </div>
          </div>

          <div className="flex-1">
            <h4 className="text-sm font-black text-[#1C1924]">You’re parked</h4>
            <p className="text-[11px] text-[#666173] mt-0.5 leading-snug">
              Until 5:00 PM today. Bay A-04 at Indiranagar Metro Hub.
            </p>
            <button className="mt-2 text-[10px] font-bold text-[#6E5BC4] bg-[#EFEBF9] px-2 py-0.5 rounded-full">
              Extend Time +
            </button>
          </div>
        </div>

        {/* Real AccessPass Card (From booking/[id].tsx) */}
        <div className="bg-[rgba(255,255,255,0.85)] backdrop-blur-xl rounded-[28px] p-4 border border-[rgba(215,210,230,0.7)] shadow-[0_12px_28px_rgba(45,35,70,0.08)] text-center space-y-3">
          <span className="text-[10px] font-black text-[#666173] uppercase tracking-widest block">
            Show at the entrance
          </span>

          {/* QR Code White Tile */}
          <div className="inline-block p-4 bg-[#FFFFFF] rounded-2xl shadow-[2px_4px_12px_rgba(45,35,70,0.08)] border border-[rgba(215,210,230,0.6)]">
            <div className="w-28 h-28 flex flex-col items-center justify-center relative">
              {/* Realistic QR Matrix Pattern */}
              <div className="grid grid-cols-6 gap-1.5 w-full h-full p-1">
                <div className="bg-[#1B1822] col-span-2 row-span-2 rounded-[3px]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822] col-span-2 row-span-2 rounded-[3px]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822] col-span-2 row-span-2 rounded-[3px]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
                <div className="bg-[#1B1822]" />
              </div>
            </div>
          </div>

          <p className="text-[11px] text-[#666173] font-medium">or tell the host your PIN</p>

          {/* Real Recessed Clay PIN Wells (width: 42, height: 52, borderRadius: 16) */}
          <div className="flex justify-center gap-1.5">
            {["8", "4", "1", "9", "0", "2"].map((d, i) => (
              <div
                key={i}
                className="w-10 h-12 rounded-2xl bg-[#F2F0F7] shadow-[inset_2px_2px_4px_rgba(45,35,70,0.12),inset_-2px_-2px_4px_rgba(255,255,255,0.85)] flex items-center justify-center text-lg font-black text-[#1C1924]"
              >
                {d}
              </div>
            ))}
          </div>

          <div className="pt-2 border-t border-[rgba(215,210,230,0.5)]">
            <span className="text-[10px] text-[#2F8A6A] font-semibold flex items-center justify-center gap-1">
              <CheckCircle2 size={12} /> Works 100% offline in underground basements
            </span>
          </div>
        </div>

        {/* Directions Button */}
        <button className="w-full bg-[#FFFFFF] border border-[rgba(215,210,230,0.8)] text-[#1C1924] font-bold py-2.5 rounded-2xl text-xs flex items-center justify-center gap-2 shadow-xs active:scale-98">
          <Navigation size={14} className="text-[#6E5BC4]" />
          <span>Get Directions in Google Maps</span>
        </button>
      </div>
    </AppBackdrop>
  );
}
