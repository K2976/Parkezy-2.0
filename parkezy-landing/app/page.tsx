import Navbar from "@/components/Navbar";
import PhoneShowcase from "@/components/PhoneShowcase";
import ComparisonSection from "@/components/ComparisonSection";
import FaqSection from "@/components/FaqSection";
import FinalCTA from "@/components/FinalCTA";

export default function Home() {
  return (
    <main className="bg-white min-h-screen text-[#0F172A] selection:bg-blue-600 selection:text-white">
      <Navbar />
      <PhoneShowcase />
      <ComparisonSection />
      <FaqSection />
      <FinalCTA />
    </main>
  );
}
