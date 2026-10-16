"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const faqs = [
  {
    q: "How does the Offline Gate PIN work in underground basements?",
    a: "When you book a parking spot, Parkezy issues a cryptographically signed 6-digit access PIN and dynamic QR code directly to your phone. Even in multi-level underground basements where 4G/5G signals drop to zero, your pass remains 100% active. You simply punch the 6 digits into the barrier keypad or scan the offline QR code at the scanner to raise the boom gate.",
  },
  {
    q: "How do Hosts make money on Parkezy?",
    a: "Anyone with an empty driveway, society bay, or commercial garage can register as a Parkezy Host in under 3 minutes. You set your own hourly rates, choose when spots are available (24/7 or specific hours), and toggle slots live. When drivers book, earnings accumulate in your host balance and are automatically deposited into your verified bank account.",
  },
  {
    q: "Can I reserve EV charging stations in advance?",
    a: "Yes! Parkezy has dedicated EV filters that allow you to locate and reserve parking bays equipped with certified AC and DC fast chargers. Your charging port is guaranteed and reserved exclusively for your vehicle.",
  },
  {
    q: "What payment options are supported?",
    a: "We support instant online payments powered by Razorpay, including UPI (Google Pay, PhonePe, Paytm, BHIM), credit and debit cards (Visa, Mastercard, RuPay), and NetBanking. Automated GST invoices are instantly generated for every booking.",
  },
  {
    q: "What if I arrive late or need to extend my parking time?",
    a: "You can extend your reservation with 1 tap directly from the app's Active Pass screen anytime before your booking window ends. If your spot is booked by another driver immediately after, Parkezy will proactively suggest nearby alternative bays.",
  },
];

export default function FaqSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section id="faq" className="py-24 max-w-4xl mx-auto px-6 md:px-8 text-left">
      <div className="text-center mb-16">
        <span className="text-xs font-bold text-[#6E5BC4] uppercase tracking-widest block mb-2">
          Frequently Asked Questions
        </span>
        <h2 className="text-3xl md:text-5xl font-black text-[#1C1924] tracking-tight">
          Got questions? We've got answers.
        </h2>
      </div>

      <div className="space-y-4">
        {faqs.map((faq, i) => {
          const isOpen = openIndex === i;
          return (
            <div
              key={i}
              className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-xs transition-colors"
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full px-6 py-5 flex items-center justify-between text-left font-bold text-base md:text-lg text-[#0F172A] gap-4"
              >
                <span>{faq.q}</span>
                <ChevronDown
                  size={18}
                  className={`text-slate-400 shrink-0 transition-transform duration-300 ${
                    isOpen ? "rotate-180 text-blue-600" : ""
                  }`}
                />
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  >
                    <div className="px-6 pb-6 text-slate-600 text-sm md:text-base leading-relaxed border-t border-slate-100 pt-3">
                      {faq.a}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
