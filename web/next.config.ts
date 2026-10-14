import type { NextConfig } from "next";

// Server-side target for the /api/* rewrite. The browser calls same-origin /api/...,
// and Next.js proxies it to the FastAPI backend, so no CORS setup is needed.
const apiTarget = (
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiTarget}/api/:path*` }];
  },
};

export default nextConfig;
