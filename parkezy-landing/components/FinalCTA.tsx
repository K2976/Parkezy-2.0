"use client";

import { motion } from "framer-motion";
import PhoneScreenExplore from "./PhoneScreenExplore";
import PhoneScreenAccess from "./PhoneScreenAccess";

export default function FinalCTA() {
  return (
    <section id="download" className="pt-28 md:pt-36 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 md:px-8">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="bg-gradient-to-br from-[#2E2A35] via-[#1F1C25] to-[#363040] rounded-[32px] md:rounded-[40px] px-6 py-10 md:px-14 md:py-16 flex flex-col lg:flex-row items-center justify-between gap-12 relative shadow-2xl border border-[rgba(215,210,230,0.2)] overflow-hidden"
        >
          {/* Decorative Background Glows */}
          <div className="absolute top-0 right-1/4 w-96 h-96 bg-[#6E5BC4]/15 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 w-80 h-80 bg-[#2F8A6A]/10 rounded-full blur-3xl pointer-events-none" />

          {/* Left Text Content */}
          <div className="w-full lg:w-[55%] z-10 relative text-left">
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-black text-white tracking-tight mb-6 leading-[1.08]">
              Never circle the block <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#A495E6] to-[#7CC6A8]">
                ever again.
              </span>
            </h2>

            <p className="text-base md:text-lg text-slate-300 max-w-lg mb-10 leading-relaxed font-normal">
              Join thousands of daily commuters and travelers saving 25+ minutes per trip with instant slot reservations and contactless gate access.
            </p>

            {/* App Store Badges */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <a
                href="#"
                className="bg-white hover:bg-slate-100 transition-colors rounded-[16px] flex items-center px-4 py-2.5 gap-3 h-[56px] min-w-[170px] shadow-lg text-slate-900 active:scale-98"
              >
                <img src="/apple.svg" alt="Apple" className="h-[26px] w-auto invert" />
                <div className="flex flex-col items-start justify-center text-left">
                  <span className="text-[11px] text-slate-500 font-medium leading-none">Download on</span>
                  <span className="text-[18px] font-bold text-slate-900 leading-none mt-1">App Store</span>
                </div>
              </a>

              <a
                href="/download/android"
                className="bg-white hover:bg-slate-100 transition-colors rounded-[16px] flex items-center px-4 py-2.5 gap-3 h-[56px] min-w-[170px] shadow-lg text-slate-900 active:scale-98"
              >
                <img src="/android.svg" alt="Android" className="h-[26px] w-auto invert" />
                <div className="flex flex-col items-start justify-center text-left">
                  <span className="text-[11px] text-slate-500 font-medium leading-none">Download for</span>
                  <span className="text-[18px] font-bold text-slate-900 leading-none mt-1">Android</span>
                </div>
              </a>
            </div>

            {/* Host Banner Callout */}
            <div className="mt-10 pt-8 border-t border-slate-800">
              <p className="text-xs font-bold text-white">Have a private driveway or unused slot?</p>
              <a href="#hosts" className="text-xs text-[#A495E6] hover:text-white font-semibold inline-block mt-1 transition-colors">
                Become a Parkezy Host & Earn Passive Income
              </a>
            </div>
          </div>

          {/* Right Angled Phone Previews */}
          <div className="w-full lg:w-[45%] h-[380px] lg:h-[420px] relative mt-8 lg:mt-0">
            {/* Screen 1 (Explore) */}
            <motion.div
              initial={{ opacity: 0, x: 50, rotate: 0 }}
              whileInView={{ opacity: 1, x: 0, rotate: -5 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2, type: "spring" }}
              className="absolute right-0 top-[-60px] lg:top-[-80px] w-[230px] md:w-[270px] h-[420px] lg:h-[500px] bg-slate-900 rounded-[32px] overflow-hidden shadow-2xl border-4 border-slate-700 pointer-events-none origin-bottom-right z-20"
            >
              <div className="scale-[0.72] origin-top-left w-[140%] h-[140%]">
                <PhoneScreenExplore />
              </div>
            </motion.div>

            {/* Screen 2 (Pass) */}
            <motion.div
              initial={{ opacity: 0, x: 50, rotate: 0 }}
              whileInView={{ opacity: 1, x: 0, rotate: 7 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.4, type: "spring" }}
              className="absolute right-[40px] md:right-[90px] top-[70px] lg:top-[90px] w-[230px] md:w-[270px] h-[420px] lg:h-[500px] bg-slate-900 rounded-[32px] overflow-hidden shadow-2xl border-4 border-slate-700 pointer-events-none origin-top-left z-10"
            >
              <div className="scale-[0.72] origin-top-left w-[140%] h-[140%]">
                <PhoneScreenAccess />
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>

      {/* Footer Navigation */}
      <footer className="mt-20 pt-12 border-t border-slate-100 max-w-7xl mx-auto px-6 md:px-8 text-slate-500 text-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-12">
          <div className="flex flex-col text-left">
            <span className="text-xl font-black text-slate-900 tracking-tight">Parkezy</span>
            <span className="text-[10px] font-bold text-[#6E5BC4] tracking-wider uppercase">Smart Parking</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-8 text-xs font-semibold text-slate-600">
            <a href="#features" className="hover:text-[#6E5BC4] transition-colors">Features</a>
            <a href="#pass" className="hover:text-[#6E5BC4] transition-colors">Offline Pass</a>
            <a href="#hosts" className="hover:text-[#6E5BC4] transition-colors">Host Portal</a>
            <a href="/privacy" className="hover:text-[#6E5BC4] transition-colors">Privacy Policy</a>
            <a href="/terms" className="hover:text-[#6E5BC4] transition-colors">Terms of Service</a>
          </div>

          <p className="text-xs text-slate-400">
            © 2026 Parkezy Technologies Pvt Ltd. All rights reserved.
          </p>
        </div>
      </footer>

      {/* Watermark Logo */}
      <div className="w-full overflow-hidden flex justify-center items-end pointer-events-none select-none">
        <h1 className="text-[34vw] md:text-[24vw] font-black text-[#C4B5EE] leading-none tracking-tighter text-center mb-[-5vw]">
          Parkezy
        </h1>
      </div>
    </section>
  );
}
