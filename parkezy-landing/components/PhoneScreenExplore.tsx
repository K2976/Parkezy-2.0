"use client";

import React from "react";
import { Search, SlidersHorizontal, Locate, Calendar, List, Navigation } from "lucide-react";
import ParkezyMockTabBar from "./ParkezyMockTabBar";

export default function PhoneScreenExplore() {
  return (
    <div className="w-full h-full bg-[#FFFFFF] text-[#1C1924] flex flex-col relative overflow-hidden select-none font-sans">
      {/* Real Map Canvas Background */}
      <div className="absolute inset-0 z-0 bg-[#F4F3F0]">
        {/* Realistic vector map SVG (roads, blocks, greenery) */}
        <svg className="w-full h-full" viewBox="0 0 390 844" fill="none" preserveAspectRatio="none">
          {/* Water body */}
          <path d="M 280 0 Q 340 180 390 220 L 390 0 Z" fill="#DCEBFA" />
          
          {/* Green Parks */}
          <rect x="20" y="160" width="110" height="130" rx="16" fill="#E2F0D9" />
          <path d="M 240 320 Q 320 300 370 380 L 320 440 L 220 390 Z" fill="#E2F0D9" />
          <rect x="25" y="490" width="85" height="120" rx="12" fill="#E2F0D9" />

          {/* Secondary Roads */}
          <path d="M -10 130 L 400 130" stroke="#FFFFFF" strokeWidth="12" />
          <path d="M -10 320 L 400 300" stroke="#FFFFFF" strokeWidth="14" />
          <path d="M -10 480 L 400 480" stroke="#FFFFFF" strokeWidth="10" />
          <path d="M 140 -10 L 140 850" stroke="#FFFFFF" strokeWidth="14" />
          <path d="M 260 -10 L 260 850" stroke="#FFFFFF" strokeWidth="12" />
          <path d="M 40 -10 L 40 850" stroke="#FFFFFF" strokeWidth="8" />

          {/* Primary Arterial Highway (Yellow tint like Google Maps) */}
          <path d="M -20 220 Q 140 240 230 400 T 410 600" stroke="#FEE8A2" strokeWidth="18" />
          <path d="M -20 220 Q 140 240 230 400 T 410 600" stroke="#F59E0B" strokeWidth="2" strokeDasharray="6 6" />

          {/* Buildings & Blocks */}
          <rect x="160" y="150" width="45" height="55" rx="4" fill="#E8E6DF" />
          <rect x="160" y="215" width="45" height="40" rx="4" fill="#E8E6DF" />
          <rect x="50" y="40" width="70" height="70" rx="6" fill="#E8E6DF" />
          <rect x="160" y="340" width="80" height="90" rx="6" fill="#E8E6DF" />
          <rect x="280" y="220" width="75" height="65" rx="6" fill="#E8E6DF" />
        </svg>

        {/* 1000m User Proximity Zone Circle */}
        <div className="absolute top-[310px] left-[70px] w-64 h-64 rounded-full border border-blue-400/30 bg-blue-500/5 pointer-events-none" />

        {/* User Location Puck with Compass Beacon */}
        <div className="absolute top-[410px] left-[175px] z-10 flex items-center justify-center pointer-events-none">
          <div className="w-14 h-14 bg-blue-500/20 rounded-full animate-ping absolute" />
          {/* Compass direction cone */}
          <div className="w-0 h-0 border-l-[14px] border-l-transparent border-r-[14px] border-r-transparent border-b-[26px] border-b-blue-500/35 -translate-y-4" />
          <div className="w-5 h-5 bg-[#2563EB] rounded-full border-2 border-white shadow-[0_2px_8px_rgba(37,99,235,0.6)] absolute" />
        </div>

        {/* Real Pin 1: Nearest Spot (Active, Raised White Clay Pill) */}
        <div className="absolute top-[280px] left-[155px] z-20 flex flex-col items-center">
          <div className="bg-[#FFFFFF] text-[#1C1924] rounded-full px-3 py-1 shadow-[2px_4px_12px_rgba(45,35,70,0.18)] border border-[rgba(215,210,230,0.8)] flex items-center gap-1.5 transform hover:scale-105 transition-transform">
            <span className="w-2 h-2 rounded-full bg-[#2F8A6A] animate-pulse" />
            <span className="text-xs font-black text-[#6E5BC4] font-mono">₹40/hr</span>
          </div>
          <div className="w-2.5 h-2.5 bg-[#FFFFFF] rotate-45 -mt-1 shadow-sm border-r border-b border-[rgba(215,210,230,0.8)]" />
        </div>

        {/* Real Pin 2: Commercial EV Spot */}
        <div className="absolute top-[200px] left-[65px] z-10 flex flex-col items-center">
          <div className="bg-[#FFFFFF] text-[#1C1924] rounded-full px-2.5 py-0.5 shadow-[2px_3px_8px_rgba(45,35,70,0.14)] border border-[rgba(215,210,230,0.7)] flex items-center gap-1">
            <span className="text-[10px] font-black text-[#2F8A6A]">⚡ ₹65/hr</span>
          </div>
          <div className="w-2 h-2 bg-[#FFFFFF] rotate-45 -mt-1 border-r border-b border-[rgba(215,210,230,0.7)]" />
        </div>

        {/* Real Pin 3: Economy Spot */}
        <div className="absolute top-[340px] right-[45px] z-10 flex flex-col items-center">
          <div className="bg-[#FFFFFF] text-[#1C1924] rounded-full px-2.5 py-0.5 shadow-[2px_3px_8px_rgba(45,35,70,0.14)] border border-[rgba(215,210,230,0.7)] flex items-center gap-1">
            <span className="text-[10px] font-bold text-[#6E5BC4]">₹30/hr</span>
          </div>
          <div className="w-2 h-2 bg-[#FFFFFF] rotate-45 -mt-1 border-r border-b border-[rgba(215,210,230,0.7)]" />
        </div>
      </div>

      {/* Top Glass Search & Filter Controls Dock */}
      <div className="pt-3 px-4 pb-2 z-20 space-y-2 pointer-events-auto">
        {/* Status Bar */}
        <div className="flex items-center justify-between text-xs text-[#1C1924] font-bold px-2 pb-1">
          <span>9:41</span>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-2.5 border border-[#1C1924] rounded-sm p-0.5 flex items-center">
              <div className="w-full h-full bg-[#1C1924] rounded-[1px]" />
            </div>
          </div>
        </div>

        {/* Real Frosted Glass Search Bar */}
        <div className="bg-[rgba(255,255,255,0.85)] backdrop-blur-2xl rounded-2xl p-2 border border-[rgba(215,210,230,0.6)] shadow-[0_8px_20px_rgba(45,35,70,0.08)] space-y-2">
          {/* Recessed Clay Input */}
          <div className="bg-[#F2F0F7] rounded-xl px-3 py-2 flex items-center gap-2 shadow-[inset_1.5px_1.5px_3px_rgba(45,35,70,0.08),inset_-1.5px_-1.5px_3px_rgba(255,255,255,0.85)]">
            <Search size={16} className="text-[#6E5BC4]" />
            <input
              type="text"
              readOnly
              value="Indiranagar 100ft Rd, Bengaluru"
              className="w-full bg-transparent text-xs font-semibold text-[#1C1924] focus:outline-none"
            />
          </div>

          {/* Clay Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-hidden text-[10px]">
            <button className="bg-[#FFFFFF] border border-[rgba(215,210,230,0.7)] text-[#1C1924] font-bold px-2.5 py-1 rounded-full shadow-[1px_2px_4px_rgba(45,35,70,0.06)] flex items-center gap-1">
              <Calendar size={11} className="text-[#6E5BC4]" /> Now (2h)
            </button>
            <button className="bg-[#EFEBF9] border border-[#6E5BC4]/30 text-[#6E5BC4] font-bold px-2.5 py-1 rounded-full shadow-xs flex items-center gap-1">
              <SlidersHorizontal size={11} /> Filters (2)
            </button>
            <button className="bg-[#FFFFFF] border border-[rgba(215,210,230,0.7)] text-[#1C1924] font-semibold px-2 py-1 rounded-full shadow-xs flex items-center gap-1">
              <List size={11} /> List
            </button>
          </div>
        </div>
      </div>

      {/* Floating Locate Button */}
      <div className="absolute right-4 bottom-[170px] z-20">
        <button className="w-11 h-11 rounded-full bg-[#FFFFFF] border border-[rgba(215,210,230,0.7)] flex items-center justify-center text-[#1C1924] shadow-[2px_4px_12px_rgba(45,35,70,0.15)] active:scale-95 transition-transform">
          <Locate size={19} className="text-[#6E5BC4]" />
        </button>
      </div>

      {/* Real Floating Nearest Available Spot Card */}
      <div className="absolute bottom-[72px] left-3.5 right-3.5 z-20">
        <div className="bg-[rgba(255,255,255,0.92)] backdrop-blur-2xl rounded-[24px] p-3.5 border border-[rgba(215,210,230,0.75)] shadow-[0_16px_36px_rgba(45,35,70,0.16)] space-y-2.5 text-left">
          {/* Header Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#2F8A6A]" />
              <span className="text-[10px] font-black text-[#2F8A6A] tracking-wider uppercase">
                3 Spots within 1.0 km of you
              </span>
            </div>
            <div className="bg-[#EFEBF9] rounded-full px-2 py-0.5">
              <span className="text-[10px] font-bold text-[#6E5BC4]">📍 140m away</span>
            </div>
          </div>

          {/* Details Row */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-black text-[#1C1924] tracking-tight">
                Indiranagar Metro Hub
              </h4>
              <p className="text-[11px] text-[#666173]">100 Feet Rd, HAL 2nd Stage</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm font-black text-[#6E5BC4]">₹40/hr</span>
                <span className="text-[11px] text-[#666173] font-medium">● 4 bays free</span>
              </div>
            </div>

            {/* Clay "Book Spot" Button */}
            <button className="bg-[#6E5BC4] hover:bg-[#5F4DB3] text-[#FFFFFF] text-xs font-bold px-4 py-2.5 rounded-2xl shadow-[2px_4px_10px_rgba(110,91,196,0.35)] active:scale-95 transition-all">
              Book Spot
            </button>
          </div>
        </div>
      </div>

      {/* Real Glass Tab Bar */}
      <ParkezyMockTabBar activeTab="explore" />
    </div>
  );
}
