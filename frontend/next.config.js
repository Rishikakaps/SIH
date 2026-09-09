/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  outputFileTracingRoot: __dirname,
  experimental: { proxyTimeout: 150000, proxyClientMaxBodySize: "16mb" },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_BASE_URL || "http://127.0.0.1:8000"}/:path*` }];
  }
};

module.exports = nextConfig;
