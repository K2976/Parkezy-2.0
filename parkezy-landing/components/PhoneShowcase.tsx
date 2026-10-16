"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import PhoneFrame from "./PhoneFrame";
import Hero from "./Hero";
import FeatureSection from "./FeatureSection";
import PhoneScreenExplore from "./PhoneScreenExplore";
import PhoneScreenBooking from "./PhoneScreenBooking";
import PhoneScreenAccess from "./PhoneScreenAccess";
import PhoneScreenHost from "./PhoneScreenHost";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const features = [
  {
    label: "Discovery",
    title: "Find & Reserve Live Spots on Google Maps",
    description:
      "Pinpoint guaranteed parking near your destination before you even start driving. Filter in real-time by covered bays, EV charging, CCTV security, and instant entry.",
  },
  {
    label: "Instant Booking",
    title: "Guaranteed Hold & 1-Click UPI Payment",
    description:
      "Select your exact vehicle size and parking window. Lock your slot instantly with an automated 10-minute hold and check out seamlessly via UPI, PhonePe, or cards.",
  },
  {
    label: "Smart Access",
    title: "Dynamic QR & Offline Keypad PIN",
    description:
      "Never worry about poor cellular reception in underground basements. Scan rotating dynamic QR codes at boom barriers or enter your 6-digit offline PIN directly into the gate keypad.",
  },
  {
    label: "Host Monetization",
    title: "Turn Empty Driveways into Daily Income",
    description:
      "List private driveways, residential bays, or commercial lots in minutes. Toggle slot availability live, track occupancy rates, and enjoy automated direct bank payouts.",
  },
];

export default function PhoneShowcase() {
  const heroRef = useRef<HTMLDivElement>(null);
  const showcaseRef = useRef<HTMLDivElement>(null);
  const phoneRef = useRef<HTMLDivElement>(null);
  const phoneContainerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef(0);
  const [activeScreen, setActiveScreen] = useState(0);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    if (isMobile) return;

    const phone = phoneRef.current;
    const hero = heroRef.current;
    const showcase = showcaseRef.current;
    const container = phoneContainerRef.current;
    if (!phone || !hero || !showcase || !container) return;

    // Calculate offset: push phone to the right side (hero layout)
    const rightOffset = window.innerWidth * 0.22;

    const ctx = gsap.context(() => {
      // Initial state: phone offset to the right, slightly scaled down
      gsap.set(phone, { x: rightOffset, scale: 0.92 });
      gsap.set(container, { opacity: 1 });

      // ── Phase 1 ──────────────────────────────────────────────
      // Hero scroll: phone glides from right → center
      gsap.to(phone, {
        x: 0,
        scale: 1,
        ease: "none",
        scrollTrigger: {
          trigger: hero,
          start: "top top",
          end: "bottom top",
          scrub: 1.2,
        },
      });

      // ── Phase 2 ──────────────────────────────────────────────
      // Showcase scroll: track progress → swap active screen
      ScrollTrigger.create({
        trigger: showcase,
        start: "top center",
        end: "bottom bottom",
        onUpdate: (self) => {
          const idx = Math.min(
            Math.floor(self.progress * features.length),
            features.length - 1
          );
          const newScreen = idx;
          if (newScreen !== activeRef.current) {
            activeRef.current = newScreen;
            setActiveScreen(newScreen);
          }
        },
        onLeaveBack: () => {
          activeRef.current = 0;
          setActiveScreen(0);
        },
      });

      // ── Phase 3 ──────────────────────────────────────────────
      // Fade phone out as showcase ends (entering CTA section)
      gsap.to(container, {
        opacity: 0,
        ease: "none",
        scrollTrigger: {
          trigger: showcase,
          start: "bottom bottom",
          end: "bottom 30%",
          scrub: true,
        },
      });

      // ── Idle float ───────────────────────────────────────────
      gsap.to(phone, {
        y: -8,
        duration: 3,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        delay: 0.5,
      });
    });

    return () => ctx.revert();
  }, [isMobile]);

  // ═══════════════════════════════════════════════════════════
  // Mobile Fallback: stacked inline layout
  // ═══════════════════════════════════════════════════════════
  if (isMobile) {
    return (
      <div className="px-6">
        {/* Mobile Hero */}
        <section className="min-h-screen flex flex-col justify-center pt-28 pb-12">
          <Hero />
          <div className="mt-12 mx-auto w-[295px]">
            <PhoneFrame activeScreen={0} className="w-full">
              <PhoneScreenExplore />
              <PhoneScreenBooking />
              <PhoneScreenAccess />
              <PhoneScreenHost />
            </PhoneFrame>
          </div>
        </section>

        {/* Mobile Features */}
        {features.map((f, i) => {
          const screens = [
            <PhoneScreenExplore key="e" />,
            <PhoneScreenBooking key="b" />,
            <PhoneScreenAccess key="a" />,
            <PhoneScreenHost key="h" />,
          ];
          return (
            <section key={f.title} className="py-20 border-t border-slate-100 text-left">
              <div className="mb-8">
                <span className="text-xs font-bold text-[#6E5BC4] uppercase tracking-widest block mb-2">
                  {f.label}
                </span>
                <h3 className="text-2xl sm:text-3xl font-black text-[#1C1924] mb-3 tracking-tight leading-snug">
                  {f.title}
                </h3>
                <p className="text-sm sm:text-base text-slate-600 leading-relaxed font-normal">
                  {f.description}
                </p>
              </div>
              <div className="mx-auto w-[295px]">
                <PhoneFrame activeScreen={0} className="w-full">
                  {[screens[i]]}
                </PhoneFrame>
              </div>
            </section>
          );
        })}
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════
  // Desktop: GSAP ScrollTrigger Experience
  // ═══════════════════════════════════════════════════════════
  return (
    <div>
      {/* ── Fixed Phone Overlay ─────────────────────────────── */}
      <div
        ref={phoneContainerRef}
        className="fixed inset-0 z-30 pointer-events-none flex items-center justify-center translate-y-8"
      >
        <div
          ref={phoneRef}
          className="w-[300px] md:w-[325px] lg:w-[350px] will-change-transform"
        >
          <PhoneFrame activeScreen={activeScreen} className="w-full">
            <PhoneScreenExplore />
            <PhoneScreenBooking />
            <PhoneScreenAccess />
            <PhoneScreenHost />
          </PhoneFrame>
        </div>
      </div>

      {/* ── Hero Section ────────────────────────────────────── */}
      <section ref={heroRef} className="h-screen flex items-center">
        <div className="max-w-7xl mx-auto px-8 w-full">
          <div className="max-w-xl">
            <Hero />
          </div>
        </div>
      </section>

      {/* ── Feature Showcase ────────────────────────────────── */}
      <section
        ref={showcaseRef}
        style={{ height: `${features.length * 100}vh` }}
      >
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="h-screen flex items-center"
            >
              <div className="w-full">
                <FeatureSection
                  title={feature.title}
                  description={feature.description}
                  isActive={activeScreen === index}
                  index={index}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
