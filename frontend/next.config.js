/** @type {import('next').NextConfig} */
const BACKEND = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Preview-safe: the browser only talks to the Next.js origin; /api/* is
  // proxied to the FastAPI backend (never localhost from browser code).
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/docs", destination: `${BACKEND}/docs` },
      { source: "/openapi.json", destination: `${BACKEND}/openapi.json` },
    ];
  },
};

module.exports = nextConfig;
