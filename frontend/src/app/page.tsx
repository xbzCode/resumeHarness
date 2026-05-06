"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { FileText, Sparkles, Zap, ArrowRight, MessageSquare, FileOutput, Shield } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuthStore } from "@/store/auth";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] },
  }),
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] },
  }),
};

const features = [
  {
    icon: MessageSquare,
    title: "对话式生成",
    desc: "自然语言交互，上传简历和 JD，AI 自动分析并生成优化版本",
    gradient: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-500",
  },
  {
    icon: FileOutput,
    title: "多模板导出",
    desc: "商务风、学术风、创意排版，一键导出 PDF 或 Markdown",
    gradient: "from-violet-500/20 to-purple-500/20",
    iconColor: "text-violet-500",
  },
  {
    icon: Shield,
    title: "数据隔离",
    desc: "每位用户独立空间，简历和记忆数据完全隔离，安全可靠",
    gradient: "from-emerald-500/20 to-green-500/20",
    iconColor: "text-emerald-500",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="fixed top-0 z-50 w-full border-b/0 bg-background/80 backdrop-blur-xl"
      >
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold tracking-tight">Resume Agent</span>
          </Link>
          <nav className="flex items-center gap-3">
            <ThemeToggle className="h-8 w-8" />
            {hydrated && token ? (
              <Button size="sm" onClick={() => router.push("/chat")} className="gap-1.5">
                工作台
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" size="sm">登录</Button>
                </Link>
                <Link href="/register">
                  <Button size="sm">注册</Button>
                </Link>
              </>
            )}
          </nav>
        </div>
      </motion.header>

      {/* Hero */}
      <main className="flex-1">
        <section className="relative flex min-h-[92vh] items-center justify-center overflow-hidden">
          {/* 网格背景 */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage:
                "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
              backgroundSize: "60px 60px",
            }}
          />
          {/* 径向渐变光晕 */}
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,rgba(120,119,198,0.12),transparent)]" />
          {/* 顶部线性渐变 */}
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-primary/5 to-transparent" />

          <div className="relative z-10 mx-auto max-w-3xl px-6 text-center">
            {/* 标签 */}
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0}
              className="mb-8 inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-xs text-muted-foreground"
            >
              <Zap className="h-3 w-3 text-amber-500" />
              AI 驱动 · 对话式交互
            </motion.div>

            {/* 大标题 */}
            <motion.h1
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={1}
              className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl"
            >
              让简历匹配
              <br />
              <span className="bg-gradient-to-r from-primary via-primary/80 to-primary/50 bg-clip-text text-transparent">
                每一个目标岗位
              </span>
            </motion.h1>

            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={2}
              className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-muted-foreground"
            >
              上传简历和 JD，AI 自动分析匹配度、生成优化建议，
              一键输出多模板 PDF。让每一份投递都更精准。
            </motion.p>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={3}
              className="mt-10 flex items-center justify-center gap-3"
            >
              {hydrated && token ? (
                <Button size="lg" className="gap-2" onClick={() => router.push("/chat")}>
                  <Sparkles className="h-4 w-4" />
                  进入工作台
                  <ArrowRight className="h-4 w-4" />
                </Button>
              ) : (
                <>
                  <Link href="/register">
                    <Button size="lg" className="gap-2">
                      <Sparkles className="h-4 w-4" />
                      免费开始
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                  <Link href="/login">
                    <Button variant="outline" size="lg">
                      登录
                    </Button>
                  </Link>
                </>
              )}
            </motion.div>


          </div>
        </section>

        {/* Features */}
        <section className="border-t py-24">
          <div className="mx-auto max-w-5xl px-6">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              className="text-center"
            >
              <motion.h2
                variants={fadeUp}
                custom={0}
                className="text-2xl font-semibold tracking-tight"
              >
                核心能力
              </motion.h2>
              <motion.p
                variants={fadeUp}
                custom={1}
                className="mt-2 text-sm text-muted-foreground"
              >
                从分析到输出，覆盖简历优化全流程
              </motion.p>
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              className="mt-16 grid gap-6 sm:grid-cols-3"
            >
              {features.map((item, i) => {
                const Icon = item.icon;
                return (
                  <motion.div
                    key={item.title}
                    variants={scaleIn}
                    custom={i}
                    whileHover={{ y: -4, transition: { duration: 0.2 } }}
                    className="group relative flex flex-col gap-4 rounded-2xl border bg-card p-8 transition-shadow hover:shadow-lg"
                  >
                    {/* 渐变背景圆 */}
                    <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${item.gradient}`}>
                      <Icon className={`h-5 w-5 ${item.iconColor}`} />
                    </div>
                    <h3 className="font-semibold">{item.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {item.desc}
                    </p>
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t py-24">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
            >
              <motion.h2
                variants={fadeUp}
                custom={0}
                className="text-2xl font-semibold tracking-tight"
              >
                开始优化你的简历
              </motion.h2>
              <motion.p
                variants={fadeUp}
                custom={1}
                className="mt-3 text-muted-foreground"
              >
                无需信用卡，注册即可使用
              </motion.p>
              <motion.div variants={fadeUp} custom={2} className="mt-8">
                {hydrated && token ? (
                  <Button size="lg" className="gap-2" onClick={() => router.push("/chat")}>
                    进入工作台
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Link href="/register">
                    <Button size="lg" className="gap-2">
                      免费注册
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                )}
              </motion.div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-6">
        <div className="mx-auto max-w-6xl px-6 text-center text-xs text-muted-foreground">
          Resume Agent — AI 驱动的智能简历优化助手
        </div>
      </footer>
    </div>
  );
}
