import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 开发环境 API 代理，避免跨域
  async rewrites() {
    const apiTarget = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
  // 允许局域网访问时的 HMR WebSocket 连接
  allowedDevOrigins: ['192.168.3.32', 'localhost'],
};

export default nextConfig;
