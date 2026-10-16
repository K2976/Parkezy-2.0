"use client";

import React from "react";
import { Map, Calendar, Home, User } from "lucide-react";

export default function ParkezyMockTabBar({ activeTab }: { activeTab: "explore" | "bookings" | "host" | "account" }) {
  return (
    <div className="absolute bottom-5 left-4 right-4 z-30 pointer-events-none">
      <div className="w-full flex items-center justify-between bg-[rgba(255,255,255,0.88)] backdrop-blur-2xl rounded-[32px] px-2 py-1.5 border border-[rgba(215,210,230,0.7)] shadow-[0_12px_28px_rgba(45,35,70,0.12)]">
        {/* Explore */}
        <div className="flex-1 flex justify-center">
          <div
            className={`flex flex-col items-center justify-center w-[64px] h-[44px] rounded-full transition-all ${
              activeTab === "explore"
                ? "bg-[#F2F0F7] shadow-[inset_1.5px_1.5px_3px_rgba(45,35,70,0.1),inset_-1.5px_-1.5px_3px_rgba(255,255,255,0.9)]"
                : "opacity-60"
            }`}
          >
            <Map
              size={17}
              className={activeTab === "explore" ? "text-[#6E5BC4] fill-[#6E5BC4]" : "text-[#666173]"}
            />
            <span
              className={`text-[9px] mt-0.5 tracking-tight ${
                activeTab === "explore" ? "text-[#6E5BC4] font-bold" : "text-[#666173] font-medium"
              }`}
            >
              Explore
            </span>
          </div>
        </div>

        {/* Bookings */}
        <div className="flex-1 flex justify-center">
          <div
            className={`flex flex-col items-center justify-center w-[64px] h-[44px] rounded-full transition-all ${
              activeTab === "bookings"
                ? "bg-[#F2F0F7] shadow-[inset_1.5px_1.5px_3px_rgba(45,35,70,0.1),inset_-1.5px_-1.5px_3px_rgba(255,255,255,0.9)]"
                : "opacity-60"
            }`}
          >
            <Calendar
              size={17}
              className={activeTab === "bookings" ? "text-[#6E5BC4] fill-[#6E5BC4]" : "text-[#666173]"}
            />
            <span
              className={`text-[9px] mt-0.5 tracking-tight ${
                activeTab === "bookings" ? "text-[#6E5BC4] font-bold" : "text-[#666173] font-medium"
              }`}
            >
              Bookings
            </span>
          </div>
        </div>

        {/* Host */}
        <div className="flex-1 flex justify-center">
          <div
            className={`flex flex-col items-center justify-center w-[64px] h-[44px] rounded-full transition-all ${
              activeTab === "host"
                ? "bg-[#F2F0F7] shadow-[inset_1.5px_1.5px_3px_rgba(45,35,70,0.1),inset_-1.5px_-1.5px_3px_rgba(255,255,255,0.9)]"
                : "opacity-60"
            }`}
          >
            <Home
              size={17}
              className={activeTab === "host" ? "text-[#6E5BC4] fill-[#6E5BC4]" : "text-[#666173]"}
            />
            <span
              className={`text-[9px] mt-0.5 tracking-tight ${
                activeTab === "host" ? "text-[#6E5BC4] font-bold" : "text-[#666173] font-medium"
              }`}
            >
              Host
            </span>
          </div>
        </div>

        {/* Account */}
        <div className="flex-1 flex justify-center">
          <div
            className={`flex flex-col items-center justify-center w-[64px] h-[44px] rounded-full transition-all ${
              activeTab === "account"
                ? "bg-[#F2F0F7] shadow-[inset_1.5px_1.5px_3px_rgba(45,35,70,0.1),inset_-1.5px_-1.5px_3px_rgba(255,255,255,0.9)]"
                : "opacity-60"
            }`}
          >
            <User
              size={17}
              className={activeTab === "account" ? "text-[#6E5BC4] fill-[#6E5BC4]" : "text-[#666173]"}
            />
            <span
              className={`text-[9px] mt-0.5 tracking-tight ${
                activeTab === "account" ? "text-[#6E5BC4] font-bold" : "text-[#666173] font-medium"
              }`}
            >
              Account
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
