"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);

  // 等待客户端 hydration 完成（persist store 从 localStorage 恢复）
  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated && !token) {
      router.push("/login");
    }
  }, [hydrated, token, router]);

  // hydration 未完成或未认证时不渲染内容，避免 SSR/Client 不匹配
  if (!hydrated || !token) return null;

  return <>{children}</>;
}
