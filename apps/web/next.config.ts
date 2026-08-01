import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow LAN / hotspot access in `next dev` (HMR + client bundles).
  allowedDevOrigins: ["172.20.10.2", "127.0.0.1"],
};

export default nextConfig;
