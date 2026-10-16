import type { Metadata } from "next";
import { Inter, Nunito } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const nunito = Nunito({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["700", "800", "900"],
});

export const metadata: Metadata = {
  title: "Parkezy — Instant Smart Parking Discovery, Booking & Host Monetization",
  description:
    "Find, reserve, and access guaranteed parking spots in seconds. Seamless Google Maps navigation, contactless QR entry, offline-ready gate PINs, and instant UPI checkout.",
  keywords: [
    "smart parking",
    "parking app",
    "EV charging parking",
    "reserve parking spot",
    "parking monetization",
    "parkezy",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${nunito.variable} h-full antialiased`}>
      <body className="min-h-full font-sans bg-white text-[#1C1924] selection:bg-[#6E5BC4] selection:text-white">
        {children}
      </body>
    </html>
  );
}
