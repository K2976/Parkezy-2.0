"use client";

import { motion } from "framer-motion";

interface FeatureSectionProps {
  title: string;
  description: string;
  isActive: boolean;
  index: number;
}

const labels = [
  "Live Discovery",
  "Instant Booking",
  "Offline-Ready Access",
  "Host Monetization",
];

export default function FeatureSection({
  title,
  description,
  isActive,
  index,
}: FeatureSectionProps) {
  const isLeft = index % 2 === 0;

  return (
    <motion.div
      initial={false}
      animate={{
        opacity: isActive ? 1 : 0.15,
        y: isActive ? 0 : 15,
        filter: isActive ? "blur(0px)" : "blur(2.5px)",
      }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`py-8 flex flex-col md:flex-row items-center w-full text-left ${
        isLeft ? "justify-start" : "justify-end"
      }`}
    >
      <div
        className={`w-full md:w-[31%] lg:w-[28%] md:max-w-[340px] lg:max-w-[370px] ${
          isLeft ? "md:mr-auto" : "md:ml-auto"
        }`}
      >
        <span className="text-xs font-bold text-[#6E5BC4] uppercase tracking-widest block mb-2">
          {labels[index] || "Feature"}
        </span>
        <h3 className="text-2xl md:text-3xl lg:text-4xl font-black text-[#1C1924] mb-4 tracking-tight leading-[1.16]">
          {title}
        </h3>
        <p className="text-sm md:text-base lg:text-lg text-slate-600 leading-relaxed font-normal">
          {description}
        </p>
      </div>
    </motion.div>
  );
}
