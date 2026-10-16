import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/downloads/parkezy.apk",
        destination: "https://expo.dev/artifacts/eas/h3_M2O2urTM3rgidRnMwsl4ctKyK4FA3lB7rEERdp-8.apk",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
