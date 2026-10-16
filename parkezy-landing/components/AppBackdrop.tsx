"use client";

import React, { ReactNode } from "react";

export default function AppBackdrop({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`w-full h-full bg-[#FFFFFF] relative overflow-hidden text-[#1C1924] select-none ${className}`}>
      {/* Real Parkezy Ambient Background Blobs */}
      <div className="absolute -top-16 -left-12 w-64 h-64 rounded-full bg-[rgba(139,120,214,0.18)] blur-3xl pointer-events-none" />
      <div className="absolute top-[35%] -right-16 w-60 h-60 rounded-full bg-[rgba(216,139,170,0.14)] blur-3xl pointer-events-none" />
      <div className="absolute -bottom-10 -left-10 w-64 h-64 rounded-full bg-[rgba(127,179,217,0.16)] blur-3xl pointer-events-none" />
      
      {/* Screen Content */}
      <div className="relative z-10 w-full h-full flex flex-col">
        {children}
      </div>
    </div>
  );
}
