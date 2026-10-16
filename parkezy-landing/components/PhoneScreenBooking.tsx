"use client";

import React from "react";
import { ArrowLeft, Clock, ShieldCheck, Star, Car, Zap, CheckCircle2 } from "lucide-react";
import AppBackdrop from "./AppBackdrop";

export default function PhoneScreenBooking() {
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
          <span className="text-sm font-bold text-[#1C1924]">Spot Details</span>
        </div>
        <div className="bg-[#EFEBF9] text-[#6E5BC4] text-[10px] font-bold px-2.5 py-0.5 rounded-full">
          Instant Hold
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 px-4 py-3 space-y-3 overflow-y-auto pb-10 text-left">
        {/* Real Photo Card */}
        <div className="w-full h-36 rounded-2xl overflow-hidden relative shadow-[2px_6px_16px_rgba(45,35,70,0.1)] border border-[rgba(215,210,230,0.6)] bg-slate-200">
          <img
            src="https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=800&q=80"
            alt="Parking Bay"
            className="w-full h-full object-cover"
          />
          <div className="absolute top-2.5 right-2.5 bg-black/60 backdrop-blur-md rounded-full px-2 py-0.5 text-[9px] font-bold text-white">
            1/4 Photos
          </div>
          <div className="absolute bottom-2.5 left-2.5 bg-[#FFFFFF]/90 backdrop-blur-md rounded-lg px-2 py-0.5 text-[10px] font-bold text-[#2F8A6A] flex items-center gap-1 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2F8A6A]" /> Active Facility
          </div>
        </div>

        {/* Spot Title & Ratings */}
        <div>
          <div className="flex items-baseline justify-between">
            <h3 className="text-base font-black text-[#1C1924] tracking-tight">
              Indiranagar Metro Hub
            </h3>
            <span className="text-base font-black text-[#6E5BC4]">₹40/hr</span>
          </div>
          <p className="text-[11px] text-[#666173]">100 Feet Rd, HAL 2nd Stage, Bengaluru</p>
          <div className="flex items-center gap-2 mt-1 text-[11px]">
            <div className="flex items-center gap-1 text-[#A86F1C] font-bold">
              <Star size={12} className="fill-[#A86F1C]" />
              <span>4.9</span>
              <span className="text-[#666173] font-normal">(184 reviews)</span>
            </div>
            <span className="text-[#666173]">·</span>
            <span className="text-[#2F8A6A] font-semibold">CCTV & Covered</span>
          </div>
        </div>

        {/* Slot Selection (Real Clay Chips) */}
        <div>
          <span className="text-[10px] font-black text-[#666173] uppercase tracking-wider block mb-1.5">
            Select Parking Bay
          </span>
          <div className="flex gap-2">
            <div className="flex-1 bg-[#EFEBF9] border-2 border-[#6E5BC4] rounded-2xl p-2 text-center shadow-xs">
              <span className="text-[10px] font-black text-[#6E5BC4] block">Bay A-04</span>
              <span className="text-[9px] text-[#666173]">Ground Level · Car</span>
            </div>
            <div className="flex-1 bg-[#FFFFFF] border border-[rgba(215,210,230,0.8)] rounded-2xl p-2 text-center shadow-xs opacity-75">
              <span className="text-[10px] font-bold text-[#1C1924] block flex items-center justify-center gap-1">
                <Zap size={10} className="text-[#2F8A6A]" /> Bay E-02
              </span>
              <span className="text-[9px] text-[#666173]">EV Fast 22kW (₹65)</span>
            </div>
          </div>
        </div>

        {/* Real WhenPicker Card (Frosted Glass) */}
        <div className="bg-[rgba(255,255,255,0.75)] backdrop-blur-xl rounded-2xl p-3 border border-[rgba(215,210,230,0.6)] shadow-[2px_4px_12px_rgba(45,35,70,0.06)] space-y-2">
          <span className="text-[10px] font-black text-[#666173] uppercase tracking-wider block">
            Parking Duration
          </span>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Clock size={15} className="text-[#6E5BC4]" />
              <div>
                <p className="font-bold text-[#1C1924]">Today, 2:00 PM – 5:00 PM</p>
                <p className="text-[10px] text-[#666173]">3 Hours Duration</p>
              </div>
            </div>
            <span className="text-[10px] font-bold text-[#6E5BC4] bg-[#EFEBF9] px-2 py-0.5 rounded-full">
              Change
            </span>
          </div>
        </div>

        {/* Fare Breakdown Card */}
        <div className="bg-[rgba(255,255,255,0.75)] backdrop-blur-xl rounded-2xl p-3 border border-[rgba(215,210,230,0.6)] shadow-xs space-y-1.5 text-[11px]">
          <div className="flex justify-between text-[#666173]">
            <span>Base Rate (3h × ₹40)</span>
            <span className="text-[#1C1924] font-medium">₹120.00</span>
          </div>
          <div className="flex justify-between text-[#666173]">
            <span>Platform GST (18%)</span>
            <span className="text-[#1C1924] font-medium">₹21.60</span>
          </div>
          <div className="pt-2 border-t border-[rgba(215,210,230,0.6)] flex justify-between items-baseline">
            <span className="font-bold text-[#1C1924] text-xs">Total Amount</span>
            <span className="text-base font-black text-[#6E5BC4]">₹141.60</span>
          </div>
        </div>

        {/* Primary Clay Action Button */}
        <button className="w-full bg-[#6E5BC4] hover:bg-[#5F4DB3] text-[#FFFFFF] font-bold py-3 rounded-2xl text-xs flex items-center justify-center gap-2 shadow-[2px_6px_16px_rgba(110,91,196,0.35)] active:scale-98 transition-all">
          <ShieldCheck size={16} />
          <span>Pay with UPI / Razorpay · ₹141.60</span>
        </button>
      </div>
    </AppBackdrop>
  );
}
