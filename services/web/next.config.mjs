/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: false,
  },
  // Localhost-only doctor portal — no internal-mode toggle, no debug banners.
};

export default nextConfig;
