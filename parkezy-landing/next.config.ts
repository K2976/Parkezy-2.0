import type { NextConfig } from "next";

import path from "path";

const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://parkezy-api.onrender.com";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  async redirects() {
    return [
      {
        source: "/downloads/parkezy.apk",
        destination:
          process.env.NEXT_PUBLIC_APK_URL ||
          "https://github.com/honoursbhaduria/Parkezy-2.0/releases/latest/download/parkezy.apk",
        permanent: false,
      },
      // The API serves the legal documents (same text the app shows).
      { source: "/privacy", destination: `${apiUrl}/legal/privacy`, permanent: false },
      { source: "/terms", destination: `${apiUrl}/legal/terms`, permanent: false },
    ];
  },
};

export default nextConfig;
