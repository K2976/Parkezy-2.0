import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/downloads/parkezy.apk",
        destination: "https://expo.dev/artifacts/eas/4iKqrtysoRMsMXk8RLyXoCH5ogVM31_xXCiVOgJUcmg.apk",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
