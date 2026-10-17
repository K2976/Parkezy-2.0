"use client";

import Link from "next/link";
import { ArrowLeft, Download } from "lucide-react";

export default function DownloadAndroidPage() {
  // Always the newest GitHub release: each release attaches the APK as "parkezy.apk".
  const githubApkUrl = "https://github.com/honoursbhaduria/Parkezy-2.0/releases/latest/download/parkezy.apk";
  // Backup: the same build on Expo's servers.
  const mirrorApkUrl = "https://expo.dev/artifacts/eas/wnRELotnkfAZ081LEHFOdGwNJIrzx_Pvr7ZM5ttJ-94.apk";
  const apkDownloadUrl = process.env.NEXT_PUBLIC_APK_URL || githubApkUrl;

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
      <main className="max-w-4xl mx-auto w-full px-6 py-12 flex-1 flex flex-col justify-center items-center text-center z-10">
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-[#1C1924] tracking-tight mb-3">
          Install Parkezy on Android
        </h1>
        <p className="text-base text-slate-600 max-w-lg mb-8 leading-relaxed">
          Download the official installable APK directly to your Android device. Instant spot reservations, turn-by-turn navigation, and offline gate access.
        </p>

        {/* Clean, Normal Card */}
        <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-200 max-w-md w-full text-center space-y-5">
          <div>
            <h2 className="text-xl font-bold text-[#1C1924]">Parkezy App APK</h2>
            <p className="text-xs text-slate-500 mt-1">Package: com.parkezy.app • Android 8.0+</p>
          </div>

          {/* Download Buttons */}
          <div className="space-y-3">
            <a
              href={apkDownloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full bg-[#6E5BC4] hover:bg-[#5F4DB3] transition-all text-white font-semibold py-3.5 px-6 rounded-xl flex items-center justify-center gap-2.5 text-sm"
            >
              <Download size={18} />
              <span>Download APK</span>
            </a>

            <a
              href={mirrorApkUrl}
              download="parkezy.apk"
              className="w-full bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[#1C1924] font-medium py-3 px-6 rounded-xl flex items-center justify-center gap-2 text-sm transition-colors"
            >
              <Download size={16} className="text-[#6E5BC4]" />
              <span>Backup mirror (~143 MB)</span>
            </a>
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
