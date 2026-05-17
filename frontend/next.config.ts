import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 开发环境 API 代理，避免跨域
  // /api/chat 由 app/api/chat/route.ts SSE 代理处理，此处排除
  async rewrites() {
    const apiTarget = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      // 非 chat 的 API 路径走 rewrites 代理
      {
        source: "/api/auth/:path*",
        destination: `${apiTarget}/api/auth/:path*`,
      },
      {
        source: "/api/sessions/:path*",
        destination: `${apiTarget}/api/sessions/:path*`,
      },
      {
        source: "/api/resume/:path*",
        destination: `${apiTarget}/api/resume/:path*`,
      },
      {
        source: "/api/memory/:path*",
        destination: `${apiTarget}/api/memory/:path*`,
      },
      {
        source: "/api/settings/:path*",
        destination: `${apiTarget}/api/settings/:path*`,
      },
      {
        source: "/api/admin/:path*",
        destination: `${apiTarget}/api/admin/:path*`,
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
