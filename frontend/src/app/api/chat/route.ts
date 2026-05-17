import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * SSE 代理：将前端的 /api/chat 请求流式转发到后端。
 *
 * 浏览器直连后端会受 HTTP/1.1 6 连接限制，
 * SSE 长连接容易占满连接池导致所有请求 pending。
 * 通过 Next.js Route Handler 代理，浏览器只连 Next.js（localhost:3000），
 * Node.js 服务端直连后端不受浏览器连接数限制。
 *
 * 重要：支持并发 SSE 连接。每个请求创建独立的后端 fetch，
 * 不使用共享状态，确保多个会话同时流式输出互不干扰。
 */
export async function POST(request: NextRequest) {
  const token = request.headers.get("Authorization") || "";
  const body = await request.text();

  // 用 AbortController 确保客户端断连时也断开后端连接
  const controller = new AbortController();

  // 客户端断连时中止后端请求
  // 注意：使用 { once: true } 避免内存泄漏
  request.signal.addEventListener("abort", () => controller.abort(), { once: true });

  let backendRes: Response | null = null;

  try {
    backendRes = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token,
      },
      body,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      return new Response("aborted", { status: 499 });
    }
    throw err;
  }

  if (!backendRes.ok) {
    return new Response(await backendRes.text(), {
      status: backendRes.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 流式转发 SSE — 使用 ReadableStream 确保数据即时推送
  // 不对 backendRes.body 做缓冲，直接透传
  const stream = new ReadableStream({
    async start(ctrl) {
      const reader = backendRes!.body?.getReader();
      if (!reader) {
        ctrl.close();
        return;
      }

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          ctrl.enqueue(value);
        }
      } catch {
        // 客户端断连或后端关闭，静默处理
      } finally {
        ctrl.close();
        reader.releaseLock();
      }
    },
    cancel() {
      // 客户端取消时，中止后端连接
      controller.abort();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
