import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next.js 16 dev server blocks cross-origin access to dev resources. The
  // app is meant to be reached via http://127.0.0.1:3000 — the origin the
  // backend CORS allows for cookie-based auth (SameSite=Lax requires the
  // frontend and API on the same host). Allow it in dev only.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
