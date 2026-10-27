import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Opening the dev server by its network address (for example from a phone on the same Wi-Fi)
  // needs that host to be allowed; localhost always is. Each `*` is one label, so these cover the
  // private ranges only. See README "Use it from another device".
  allowedDevOrigins: ["10.*.*.*", "192.168.*.*", "172.*.*.*"],
};

export default nextConfig;
