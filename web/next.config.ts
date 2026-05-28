import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'zabvdgnucfanvbjjgnic.supabase.co' },
    ],
  },
};

export default nextConfig;
