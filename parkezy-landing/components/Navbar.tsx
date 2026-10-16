"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Smart Pass", href: "#pass" },
  { label: "For Hosts", href: "#hosts" },
  { label: "FAQ", href: "#faq" },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/85 backdrop-blur-xl border-b border-slate-100/80 transition-all">
      <div className="max-w-7xl mx-auto px-6 md:px-8 py-4 md:py-5 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex flex-col text-left group">
          <span className="text-2xl font-black text-[#1C1924] tracking-tight leading-none group-hover:text-[#6E5BC4] transition-colors">
            Parkezy
          </span>
          <span className="text-[10px] font-bold text-[#6E5BC4] tracking-wider uppercase mt-1">
            Smart Parking
          </span>
        </a>

        {/* Desktop Navigation & Actions */}
        <div className="hidden md:flex items-center gap-8">
          <ul className="flex items-center gap-7">
            {navLinks.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="text-slate-600 hover:text-blue-600 transition-colors text-sm font-semibold tracking-tight"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          {/* App Badges */}
          <div className="flex items-center gap-3">
            <a
              href="#download"
              className="bg-[#0F172A] hover:bg-black transition-colors rounded-[12px] flex items-center px-3 py-2 gap-2.5 h-[42px] min-w-[130px] shadow-sm active:scale-98"
            >
              <img src="/apple.svg" alt="Apple" className="h-[18px] w-auto" />
              <div className="flex flex-col items-start justify-center text-left">
                <span className="text-[9px] text-slate-400 font-medium leading-none">Get on</span>
                <span className="text-[14px] font-bold text-white leading-none mt-0.5">App Store</span>
              </div>
            </a>

            <a
              href="/download/android"
              className="bg-[#0F172A] hover:bg-black transition-colors rounded-[12px] flex items-center px-3 py-2 gap-2.5 h-[42px] min-w-[130px] shadow-sm active:scale-98"
            >
              <img src="/android.svg" alt="Android" className="h-[18px] w-auto" />
              <div className="flex flex-col items-start justify-center text-left">
                <span className="text-[9px] text-slate-400 font-medium leading-none">Get on</span>
                <span className="text-[14px] font-bold text-white leading-none mt-0.5">Google Play</span>
              </div>
            </a>
          </div>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden p-2.5 rounded-xl hover:bg-slate-100 transition-colors text-slate-800"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Dropdown */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="md:hidden absolute top-full left-0 right-0 bg-white/95 backdrop-blur-2xl rounded-b-3xl shadow-2xl border-b border-slate-100 px-6 py-6"
          >
            <ul className="flex flex-col divide-y divide-slate-100 text-left">
              {navLinks.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="block py-3 text-slate-800 hover:text-blue-600 transition-colors text-base font-semibold"
                    onClick={() => setMobileOpen(false)}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>

            <div className="flex flex-col sm:flex-row gap-3 mt-6 pt-4 border-t border-slate-100">
              <a
                href="#download"
                className="bg-[#0F172A] hover:bg-black transition-colors rounded-xl flex items-center justify-center px-4 py-3 gap-3 w-full"
              >
                <img src="/apple.svg" alt="Apple" className="h-[20px] w-auto" />
                <span className="text-sm font-bold text-white">Download on App Store</span>
              </a>
              <a
                href="/download/android"
                className="bg-[#0F172A] hover:bg-black transition-colors rounded-xl flex items-center justify-center px-4 py-3 gap-3 w-full"
              >
                <img src="/android.svg" alt="Android" className="h-[20px] w-auto" />
                <span className="text-sm font-bold text-white">Download for Android</span>
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
