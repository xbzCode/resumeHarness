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
  // @react-pdf/renderer 兼容性配置
  turbopack: {
    resolveAlias: {
      // canvas 是 Node.js 原生模块，浏览器环境不需要
      canvas: "",
    },
  },
  webpack: (config) => {
    // fallback：使用 --webpack 标志时仍生效
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };
    return config;
  },
};

export default nextConfig;
