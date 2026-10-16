"use client";

import { motion } from "framer-motion";

export default function Hero() {
  return (
    <div className="flex flex-col justify-center h-full max-w-xl text-left">

      {/* Main heading */}
      <div className="mb-6">
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-6xl md:text-7xl lg:text-8xl font-black text-[#1C1924] leading-[0.92] tracking-tight"
        >
          Park Smarter.
        </motion.h1>
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.35 }}
          className="text-6xl md:text-7xl lg:text-8xl font-black text-[#6E5BC4] leading-[0.92] tracking-tight mt-1 md:mt-2"
        >
          Arrive Faster.
        </motion.h1>
      </div>

      {/* Subtitle */}
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5 }}
        className="text-lg md:text-xl text-slate-600 max-w-lg mb-8 leading-relaxed font-normal"
      >
        Never circle the block again. Discover live nearby parking spots, reserve your bay in 2 taps, and unlock gate barriers with dynamic QR codes or offline PINs.
      </motion.p>

      {/* Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.65 }}
        className="flex flex-wrap items-center gap-4"
      >
        <a
          href="#download"
          className="bg-[#0F172A] hover:bg-black transition-all rounded-[14px] flex items-center px-4 py-2.5 gap-3 h-[54px] min-w-[160px] shadow-lg shadow-slate-900/10 hover:shadow-slate-900/20 active:scale-98"
        >
          <img src="/apple.svg" alt="Apple" className="h-[26px] w-auto" />
          <div className="flex flex-col items-start justify-center text-left">
            <span className="text-[11px] text-slate-300 font-medium leading-none">Download for</span>
            <span className="text-[19px] font-bold text-white leading-none mt-1">iOS</span>
          </div>
        </a>

        <a
          href="/download/android"
          className="bg-[#0F172A] hover:bg-black transition-all rounded-[14px] flex items-center px-4 py-2.5 gap-3 h-[54px] min-w-[160px] shadow-lg shadow-slate-900/10 hover:shadow-slate-900/20 active:scale-98"
        >
          <img src="/android.svg" alt="Android" className="h-[26px] w-auto" />
          <div className="flex flex-col items-start justify-center text-left">
            <span className="text-[11px] text-slate-300 font-medium leading-none">Download for</span>
            <span className="text-[19px] font-bold text-white leading-none mt-1">Android</span>
          </div>
        </a>
      </motion.div>

    </div>
  );
}
