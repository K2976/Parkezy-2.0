"use client";

import React from "react";
import { Car, Calendar, Hourglass, Plus, ChevronRight, Zap } from "lucide-react";
import AppBackdrop from "./AppBackdrop";
import ParkezyMockTabBar from "./ParkezyMockTabBar";

export default function PhoneScreenHost() {
  const barHeights = [45, 60, 35, 70, 85, 100, 95, 50, 65, 40, 80, 90, 100, 92];

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

      {/* Screen Title (from ScreenTitle.tsx) */}
      <div className="px-5 pt-1 pb-2 flex items-baseline justify-between text-left">
        <div>
          <h2 className="text-xl font-black text-[#1C1924] tracking-tight">Host</h2>
          <p className="text-[11px] text-[#666173]">3 live spots</p>
        </div>
        <button className="bg-[#6E5BC4] text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-xs flex items-center gap-1">
          <Plus size={11} /> New Spot
        </button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 px-4 py-2 space-y-3 overflow-y-auto pb-24 text-left">
        {/* Real FeaturedCard (The one solid surface that breaks the glass pattern) */}
        <div className="bg-[#2E2A35] rounded-[24px] p-4 text-white shadow-[0_12px_24px_rgba(46,42,53,0.25)] space-y-2.5">
          <div>
            <span className="text-[10px] font-bold text-[#C9C3D3] uppercase tracking-wider block">
              Earned in the last 14 days
            </span>
            <div className="text-2xl font-black text-[#FFFFFF] mt-0.5 font-mono">
              ₹34,850.00
            </div>
          </div>

          {/* Real BarChart (from mobile/src/ui/charts.tsx) */}
          <div className="pt-2 border-t border-white/10">
            <div className="h-14 flex items-end justify-between gap-1">
              {barHeights.map((h, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    style={{ height: `${h}%` }}
                    className={`w-full rounded-t-sm transition-all ${
                      i >= 11 ? "bg-[#A495E6]" : "bg-[#6E5BC4]/70"
                    }`}
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-between text-[8px] text-[#C9C3D3] mt-1 font-mono">
              <span>Oct 03</span>
              <span>Today</span>
            </div>
          </div>
        </div>

        {/* Real Stat Cards (Row gap={spacing.sm}) */}
        <div className="grid grid-cols-3 gap-2">
          {/* Active */}
          <div className="bg-[rgba(255,255,255,0.8)] backdrop-blur-xl rounded-2xl p-2.5 border border-[rgba(215,210,230,0.6)] shadow-xs">
            <div className="w-7 h-7 rounded-full bg-[#EFEBF9] flex items-center justify-center text-[#6E5BC4] mb-1">
              <Car size={13} />
            </div>
            <span className="text-base font-black text-[#1C1924] block">3</span>
            <span className="text-[9px] text-[#666173] font-semibold">Active</span>
          </div>

          {/* Upcoming */}
          <div className="bg-[rgba(255,255,255,0.8)] backdrop-blur-xl rounded-2xl p-2.5 border border-[rgba(215,210,230,0.6)] shadow-xs">
            <div className="w-7 h-7 rounded-full bg-[#EFEBF9] flex items-center justify-center text-[#6E5BC4] mb-1">
              <Calendar size={13} />
            </div>
            <span className="text-base font-black text-[#1C1924] block">18</span>
            <span className="text-[9px] text-[#666173] font-semibold">Upcoming</span>
          </div>

          {/* Requests */}
          <div className="bg-[rgba(255,255,255,0.8)] backdrop-blur-xl rounded-2xl p-2.5 border border-[rgba(215,210,230,0.6)] shadow-xs">
            <div className="w-7 h-7 rounded-full bg-[#FBF2E3] flex items-center justify-center text-[#A86F1C] mb-1">
              <Hourglass size={13} />
            </div>
            <span className="text-base font-black text-[#1C1924] block">2</span>
            <span className="text-[9px] text-[#666173] font-semibold">Requests</span>
          </div>
        </div>

        {/* Real Manage Slots Section (Matching host/listing/[id].tsx updated layout) */}
        <div className="bg-[rgba(255,255,255,0.8)] backdrop-blur-xl rounded-2xl p-3 border border-[rgba(215,210,230,0.6)] shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black text-[#666173] uppercase tracking-wider">
              Manage Slots (3 active)
            </span>
            <span className="text-[10px] font-bold text-[#6E5BC4]">Edit</span>
          </div>

          {/* Slot 1 */}
          <div className="bg-white rounded-xl p-2.5 border border-[rgba(215,210,230,0.5)] shadow-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-[#1C1924]">Bay 1 (Driveway)</p>
                <p className="text-[10px] text-[#666173]">Standard · ₹40/h</p>
              </div>
              {/* Real Clay Toggle Switch (track + raised knob) */}
              <div className="w-11 h-6 rounded-full bg-[#EFEBF9] p-0.5 flex items-center justify-end shadow-inner cursor-pointer">
                <div className="w-5 h-5 rounded-full bg-[#6E5BC4] shadow-[0_2px_4px_rgba(110,91,196,0.4)]" />
              </div>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[9px]">
              <span className="text-[#2F8A6A] font-bold">● Active · Available</span>
              <span className="text-[#666173]">Booked 4h today</span>
            </div>
          </div>

          {/* Slot 2 */}
          <div className="bg-white rounded-xl p-2.5 border border-[rgba(215,210,230,0.5)] shadow-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-[#1C1924] flex items-center gap-1">
                  <Zap size={11} className="text-[#2F8A6A]" /> Bay 2 (EV Port)
                </p>
                <p className="text-[10px] text-[#666173]">Fast DC 50kW · ₹75/h</p>
              </div>
              <div className="w-11 h-6 rounded-full bg-[#EFEBF9] p-0.5 flex items-center justify-end shadow-inner cursor-pointer">
                <div className="w-5 h-5 rounded-full bg-[#6E5BC4] shadow-[0_2px_4px_rgba(110,91,196,0.4)]" />
              </div>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[9px]">
              <span className="text-[#A86F1C] font-bold">● Occupied until 4:30 PM</span>
              <span className="text-[#666173]">₹300 collected</span>
            </div>
          </div>
        </div>
      </div>

      {/* Real Glass Tab Bar */}
      <ParkezyMockTabBar activeTab="host" />
    </AppBackdrop>
  );
}
