import { ofetch } from "ofetch";
import { useAuthStore } from "@/store/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export { API_BASE };

export const api = ofetch.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

/** 带认证的请求实例，401 时直接清除认证并跳转登录页 */
export function createAuthApi(token: string) {
  return ofetch.create({
    baseURL: API_BASE,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    async onResponseError({ response }) {
      if (response.status === 401) {
        if (typeof window !== "undefined") {
          useAuthStore.getState().clearAuth();
          window.location.href = "/login";
        }
      }
    },
  });
}

/** 带认证的 fetch 请求，401 时直接清除认证并跳转登录页 */
async function authFetch(token: string, path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      useAuthStore.getState().clearAuth();
      window.location.href = "/login";
    }
  }

  return res;
}

/** 下载文件（返回 Blob） */
export async function downloadFile(token: string, path: string): Promise<Blob> {
  const res = await authFetch(token, path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}

/** 获取文本响应 */
export async function fetchText(token: string, path: string): Promise<string> {
  const res = await authFetch(token, path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

/** 获取 JSON 响应 */
export async function fetchJson<T = unknown>(token: string, path: string): Promise<T> {
  const res = await authFetch(token, path, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- 类型定义 ----

export interface User {
  user_id: string;
  username: string;
  email?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
}

export interface SessionInfo {
  session_id: string;
  summary: string;
  message_count: number;
  model: string;
  created_at: number;
  updated_at: number;
}

export interface ResumeInfo {
  resume_id: string;
  created_at: number;
  size_bytes: number;
}

export interface MemoryDoc {
  name: string;
  content?: string;
  size_bytes: number;
  modified_at: number;
  writable: boolean;
}

export interface ChatRequest {
  prompt: string;
  session_id?: string;
}

export interface SessionDetail {
  session_id: string;
  found: boolean;
  summary?: string;
  model?: string;
  message_count?: number;
  created_at?: number;
  messages?: SessionMessage[];
  error?: string;
}

export interface SessionMessage {
  role: string;
  content: { type: string; text?: string; tool_use_id?: string; name?: string; input?: object; content?: string; is_error?: boolean }[];
}

// ---- SSE 流式对话 ----

export async function streamChat(
  token: string,
  body: ChatRequest,
  onEvent: (event: MessageEvent) => void,
  onError?: (err: Error) => void,
  onDone?: () => void,
): Promise<() => void> {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        if (response.status === 401) {
          useAuthStore.getState().clearAuth();
          window.location.href = "/login";
          return;
        }
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              onDone?.();
              return;
            }
            try {
              const parsed = JSON.parse(data);
              const event = new MessageEvent("message", { data: parsed });
              onEvent(event);
            } catch {
              // 非 JSON 数据，忽略
            }
          }
        }
      }
      onDone?.();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  return () => controller.abort();
}
