"use client";

// eslint-disable-next-line @next/next/no-async-client-component
export const dynamic = "force-dynamic";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold">出错了</h2>
            <p className="mt-2 text-muted-foreground">{error.message}</p>
            <button
              onClick={reset}
              className="mt-4 rounded-md bg-primary px-4 py-2 text-primary-foreground"
            >
              重试
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
