import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FileText, Sparkles, Zap, Shield } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-lg font-semibold">Resume Agent</span>
          </div>
          <nav className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">登录</Button>
            </Link>
            <Link href="/register">
              <Button size="sm">注册</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <section className="container mx-auto px-4 py-24 text-center">
          <div className="mx-auto max-w-3xl">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              AI 驱动的
              <span className="text-primary"> 智能简历优化</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              结合你的简历与目标岗位 JD，智能生成匹配度更高的优化简历。
              支持多模板、PDF 导出、对话式交互。
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link href="/register">
                <Button size="lg" className="gap-2">
                  <Sparkles className="h-4 w-4" />
                  免费开始
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="outline" size="lg">
                  已有账号，登录
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t bg-muted/40 py-20">
          <div className="container mx-auto px-4">
            <div className="mx-auto grid max-w-4xl gap-8 md:grid-cols-3">
              <div className="flex flex-col items-center text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Zap className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">对话式生成</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  自然语言交互，上传简历和 JD，AI 自动分析并生成优化版本
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">多模板导出</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  商务风、学术风、创意排版，一键导出 PDF 或 Markdown
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Shield className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">数据隔离</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  每位用户独立空间，简历和记忆数据完全隔离，安全可靠
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-6 text-center text-sm text-muted-foreground">
        <p>Resume Agent — 智能简历助手</p>
      </footer>
    </div>
  );
}
