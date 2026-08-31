import type { NextConfig } from "next";

// Every browser call goes to /api/* on this same origin and is proxied to FastAPI from
// the server side. That keeps the backend free of CORS configuration and lets the same
// build run locally (localhost) or in compose (http://api:8000) by changing one variable.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8010";

const nextConfig: NextConfig = {
  // The repo root holds other lockfiles, so name this directory explicitly rather than
  // letting Turbopack infer a workspace root.
  turbopack: { root: import.meta.dirname },
  // Next regenerates AGENTS.md/CLAUDE.md here on every dev run; the curated guidance for
  // this repo lives in the root CLAUDE.md instead.
  agentRules: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
