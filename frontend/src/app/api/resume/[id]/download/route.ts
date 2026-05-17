import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * 下载代理：将前端的 /api/resume/:id/download 请求转发到后端。
 *
 * 不走 Next.js rewrites，而是通过 Route Handler 流式代理，
 * 避免 rewrites 对大体积二进制响应（PDF/DOCX）的大小限制或超时。
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = request.headers.get("Authorization") || "";
  const searchParams = request.nextUrl.searchParams;
  const format = searchParams.get("format") || "pdf";
  const template = searchParams.get("template") || "professional";

  const backendUrl = `${BACKEND_URL}/api/resume/${id}/download?format=${format}&template=${template}`;

  const controller = new AbortController();
  request.signal.addEventListener("abort", () => controller.abort(), { once: true });

  let backendRes: Response | null = null;

  try {
    backendRes = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Authorization: token,
      },
      signal: controller.signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      return new Response("aborted", { status: 499 });
    }
    throw err;
  }

  if (!backendRes.ok) {
    const text = await backendRes.text();
    return new Response(text, {
      status: backendRes.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 流式转发二进制响应
  const contentType = backendRes.headers.get("Content-Type") || "application/octet-stream";
  const contentDisposition = backendRes.headers.get("Content-Disposition");

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
      controller.abort();
    },
  });

  const headers: Record<string, string> = {
    "Content-Type": contentType,
  };
  if (contentDisposition) {
    headers["Content-Disposition"] = contentDisposition;
  }

  return new Response(stream, { headers });
}
