"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ChevronLeft, ChevronRight } from "lucide-react";
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
  const [mobileScreen, setMobileScreen] = useState(0);
  const [direction, setDirection] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const touchStartX = useRef<number | null>(null);

  const switchMobileScreen = (newIndex: number) => {
    if (newIndex === mobileScreen) return;
    setDirection(newIndex > mobileScreen ? 1 : -1);
    setMobileScreen(newIndex);
  };

  const nextSlide = useCallback(() => {
    setDirection(1);
    setMobileScreen((prev) => (prev + 1) % features.length);
  }, []);

  const prevSlide = useCallback(() => {
    setDirection(-1);
    setMobileScreen((prev) => (prev - 1 + features.length) % features.length);
  }, []);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const diffX = e.changedTouches[0].clientX - touchStartX.current;
    if (diffX > 40) {
      prevSlide();
    } else if (diffX < -40) {
      nextSlide();
    }
    touchStartX.current = null;
  };


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
  // Mobile: Interactive Animated Feature Slider
  // ═══════════════════════════════════════════════════════════
  if (isMobile) {
    const currentFeature = features[mobileScreen];
    return (
      <div className="px-5">
        {/* Mobile Hero */}
        <section className="pt-24 pb-8 flex flex-col justify-center">
          <Hero />
        </section>

        {/* Interactive Feature Slider Section */}
        <section className="py-12 border-t border-slate-100 flex flex-col items-center">
          <div className="text-center max-w-sm mb-6">
            <span className="text-xs font-bold text-[#6E5BC4] uppercase tracking-widest block mb-2">
              App Showcase
            </span>
            <h2 className="text-2xl sm:text-3xl font-black text-[#1C1924] tracking-tight">
              Experience Parkezy
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Swipe or tap tabs below to preview live features
            </p>
          </div>

          {/* Interactive Feature Tabs */}
          <div className="w-full max-w-sm mb-6 flex items-center justify-between gap-1 p-1 bg-slate-100 rounded-2xl">
            {features.map((f, i) => {
              const active = mobileScreen === i;
              return (
                <button
                  key={f.label}
                  onClick={() => switchMobileScreen(i)}
                  className={`flex-1 py-2 px-1 text-center rounded-xl text-xs font-bold transition-all ${
                    active
                      ? "bg-white text-[#6E5BC4] shadow-xs"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          {/* Phone Frame with Swipeable Touch Controls */}
          <div
            className="relative mx-auto w-[270px] sm:w-[290px] touch-pan-y"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            {/* Prev Arrow */}
            <button
              onClick={prevSlide}
              aria-label="Previous screen"
              className="absolute -left-4 sm:-left-5 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full bg-white/95 border border-slate-200 text-slate-700 shadow-md flex items-center justify-center hover:bg-slate-50 active:scale-95 transition-all"
            >
              <ChevronLeft size={18} />
            </button>

            {/* Next Arrow */}
            <button
              onClick={nextSlide}
              aria-label="Next screen"
              className="absolute -right-4 sm:-right-5 top-1/2 -translate-y-1/2 z-20 w-9 h-9 rounded-full bg-white/95 border border-slate-200 text-slate-700 shadow-md flex items-center justify-center hover:bg-slate-50 active:scale-95 transition-all"
            >
              <ChevronRight size={18} />
            </button>

            <PhoneFrame activeScreen={mobileScreen} direction={direction} className="w-full">
              <PhoneScreenExplore />
              <PhoneScreenBooking />
              <PhoneScreenAccess />
              <PhoneScreenHost />
            </PhoneFrame>
          </div>

          {/* Animated Feature Details Card */}
          <div className="w-full max-w-sm mt-8 bg-white border border-slate-200 rounded-2xl p-5 text-left transition-all">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-[#6E5BC4] uppercase tracking-wider">
                {currentFeature.label}
              </span>
              <span className="text-[11px] font-semibold text-slate-400">
                0{mobileScreen + 1} / 0{features.length}
              </span>
            </div>

            <h3 className="text-lg font-bold text-[#1C1924] mb-2 leading-snug">
              {currentFeature.title}
            </h3>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
              {currentFeature.description}
            </p>

            {/* Dots navigation */}
            <div className="flex items-center justify-center gap-2 mt-5 pt-4 border-t border-slate-100">
              {features.map((_, i) => (
                <button
                  key={i}
                  onClick={() => switchMobileScreen(i)}
                  aria-label={`Go to slide ${i + 1}`}
                  className={`h-2 rounded-full transition-all ${
                    mobileScreen === i
                      ? "w-7 bg-[#6E5BC4]"
                      : "w-2 bg-slate-200 hover:bg-slate-300"
                  }`}
                />
              ))}
            </div>
          </div>
        </section>
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
