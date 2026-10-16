"use client";

import Link from "next/link";
import { ArrowLeft, Download, ShieldCheck, Smartphone, CheckCircle2, QrCode } from "lucide-react";
import AppBackdrop from "@/components/AppBackdrop";

export default function DownloadAndroidPage() {
  const cdnApkUrl = "https://expo.dev/artifacts/eas/4iKqrtysoRMsMXk8RLyXoCH5ogVM31_xXCiVOgJUcmg.apk";
  const localApkUrl = "/downloads/parkezy.apk";
  const apkDownloadUrl = process.env.NEXT_PUBLIC_APK_URL || cdnApkUrl;

  return (
    <div className="min-h-screen bg-[#FAF9FD] relative overflow-hidden flex flex-col justify-between text-[#1C1924]">
      {/* Background blobs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#6E5BC4]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-[#2F8A6A]/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <header className="max-w-6xl mx-auto w-full px-6 py-6 flex items-center justify-between z-10">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#6E5BC4] transition-colors">
          <ArrowLeft size={16} />
          <span>Back to Home</span>
        </Link>

        <div className="flex flex-col text-right">
          <span className="text-xl font-black text-[#1C1924] tracking-tight leading-none">Parkezy</span>
          <span className="text-[9px] font-bold text-[#6E5BC4] tracking-wider uppercase mt-0.5">Android APK</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto w-full px-6 py-8 flex-1 flex flex-col justify-center items-center text-center z-10">
        {/* Release Tag */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFEBF9] border border-[#6E5BC4]/30 mb-6 shadow-xs">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-[#6E5BC4] tracking-tight">
            Parkezy v1.0.0 — Standalone Android Release
          </span>
        </div>

        <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-[#1C1924] tracking-tight mb-4">
          Install Parkezy on Android
        </h1>
        <p className="text-base md:text-lg text-slate-600 max-w-xl mb-8 leading-relaxed">
          Download the official installable APK directly to your Android device. Instant spot reservations, turn-by-turn navigation, and offline gate access.
        </p>

        {/* Action Card */}
        <div className="bg-white rounded-[32px] p-8 md:p-10 border border-slate-200/80 shadow-xl max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-[#EFEBF9] text-[#6E5BC4] flex items-center justify-center mx-auto shadow-inner">
            <Smartphone size={32} />
          </div>

          <div>
            <h2 className="text-xl font-black text-[#1C1924]">Parkezy App APK</h2>
            <p className="text-xs text-slate-500 mt-1">Package: com.parkezy.app • Android 8.0+</p>
          </div>

          {/* Download Buttons */}
          <div className="space-y-3">
            <a
              href={apkDownloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-[#6E5BC4] hover:bg-[#5F4DB3] transition-all text-white font-bold py-4 px-6 rounded-2xl shadow-lg shadow-[#6E5BC4]/30 flex items-center justify-center gap-3 text-base active:scale-98"
            >
              <Download size={20} />
              <span>Download APK Directly</span>
            </a>

            <a
              href={localApkUrl}
              download="parkezy.apk"
              className="w-full bg-white hover:bg-slate-50 border border-slate-200 text-[#1C1924] font-semibold py-3 px-6 rounded-2xl flex items-center justify-center gap-2 text-sm transition-colors"
            >
              <Download size={16} className="text-[#6E5BC4]" />
              <span>Direct Local Mirror (~137 MB)</span>
            </a>
          </div>

          <div className="flex items-center justify-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl py-2 px-3">
            <ShieldCheck size={16} className="text-emerald-600" />
            <span>Verified safe build • Signed package • Android 8.0+</span>
          </div>

          <div className="pt-2 text-xs text-slate-500">
            <a
              href="https://expo.dev/accounts/honours1234567890875432s-team/projects/parkezy/builds/3232cc2c-311a-47ae-b32d-c10534ea90d6"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[#6E5BC4] underline underline-offset-2 flex items-center justify-center gap-1.5"
            >
              <QrCode size={14} />
              <span>Scan QR Code or view build on Expo EAS</span>
            </a>
          </div>
        </div>

        {/* 3 Step Installation Guide */}
        <div className="mt-14 max-w-2xl w-full text-left">
          <h3 className="text-lg font-black text-[#1C1924] mb-6 text-center">How to install in 3 easy steps</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white/80 backdrop-blur-md rounded-2xl p-5 border border-slate-200/60 shadow-xs space-y-2">
              <div className="w-8 h-8 rounded-full bg-[#6E5BC4] text-white flex items-center justify-center font-bold text-sm">
                1
              </div>
              <h4 className="font-bold text-sm text-[#1C1924]">Download APK</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Tap the download button above from your Android phone browser.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-md rounded-2xl p-5 border border-slate-200/60 shadow-xs space-y-2">
              <div className="w-8 h-8 rounded-full bg-[#6E5BC4] text-white flex items-center justify-center font-bold text-sm">
                2
              </div>
              <h4 className="font-bold text-sm text-[#1C1924]">Allow Install</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                When prompted by your browser, tap &quot;Settings&quot; and enable &quot;Install unknown apps&quot;.
              </p>
            </div>

            <div className="bg-white/80 backdrop-blur-md rounded-2xl p-5 border border-slate-200/60 shadow-xs space-y-2">
              <div className="w-8 h-8 rounded-full bg-[#6E5BC4] text-white flex items-center justify-center font-bold text-sm">
                3
              </div>
              <h4 className="font-bold text-sm text-[#1C1924]">Start Parking</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Open Parkezy, sign in with your phone or email, and find nearby bays!
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full px-6 py-6 text-center text-xs text-slate-400 z-10">
        © 2026 Parkezy Technologies Pvt Ltd. All rights reserved.
      </footer>
    </div>
  );
}
