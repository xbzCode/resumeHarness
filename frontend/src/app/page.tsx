"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  FileText,
  Sparkles,
  Zap,
  ArrowRight,
  MessageSquare,
  FileOutput,
  Shield,
  Brain,
  Star,
  Layers,
  MessageCircleQuestion,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuthStore } from "@/store/auth";

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

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
    desc: "自然语言交互，上传简历和 JD，AI 自动分析并生成优化版本，支持多轮迭代优化",
    gradient: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-500",
  },
  {
    icon: FileOutput,
    title: "多模板导出",
    desc: "7 套精美模板（商务/学术/创意/极简/优雅/科技/紧凑），支持在线预览、原地编辑、拖拽排序",
    gradient: "from-violet-500/20 to-purple-500/20",
    iconColor: "text-violet-500",
  },
  {
    icon: Brain,
    title: "行业感知",
    desc: "互联网/金融等行业专项技能自动匹配，JD 解析与关键词分析，智能推荐最佳模板",
    gradient: "from-amber-500/20 to-orange-500/20",
    iconColor: "text-amber-500",
  },
  {
    icon: Star,
    title: "简历评分",
    desc: "5 维度加权评分（结构/内容/量化/关键词/格式），自动检测薄弱环节并给出改进建议",
    gradient: "from-rose-500/20 to-pink-500/20",
    iconColor: "text-rose-500",
  },
  {
    icon: Layers,
    title: "记忆系统",
    desc: "自动学习用户偏好与职业信息，越用越懂你，支持自定义指令注入",
    gradient: "from-emerald-500/20 to-green-500/20",
    iconColor: "text-emerald-500",
  },
  {
    icon: Shield,
    title: "数据隔离",
    desc: "每用户独立数据空间，JWT 认证 + 多租户隔离，简历与记忆完全私密",
    gradient: "from-cyan-500/20 to-teal-500/20",
    iconColor: "text-cyan-500",
  },
];

const GITHUB_URL = "https://github.com/xbzCode/resumeHarness";

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
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
              aria-label="GitHub"
            >
              <GitHubIcon className="h-4 w-4" />
            </a>
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
              AI 驱动 · 对话式交互 · 开源项目
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
              上传简历和 JD，AI 自动分析匹配度、生成优化建议与评分，
              支持 7 套模板在线预览、原地编辑、拖拽排序，一键导出 PDF/Word/HTML。
              让每一份投递都更精准。
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
                  <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="lg" className="gap-2">
                      <GitHubIcon className="h-4 w-4" />
                      GitHub
                    </Button>
                  </a>
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
              className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
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
                无需信用卡，注册即可使用 · 开源项目，欢迎贡献
              </motion.p>
              <motion.div variants={fadeUp} custom={2} className="mt-8 flex items-center justify-center gap-3">
                {hydrated && token ? (
                  <Button size="lg" className="gap-2" onClick={() => router.push("/chat")}>
                    进入工作台
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <>
                    <Link href="/register">
                      <Button size="lg" className="gap-2">
                        免费注册
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                    <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="lg" className="gap-2">
                        <GitHubIcon className="h-4 w-4" />
                        Star on GitHub
                      </Button>
                    </a>
                  </>
                )}
              </motion.div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-6">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
            <p className="text-xs text-muted-foreground">
              Resume Agent — AI 驱动的智能简历优化助手
            </p>
            <div className="flex items-center gap-4">
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                <GitHubIcon className="h-3.5 w-3.5" />
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* 右下角问题反馈按钮 */}
      <Dialog>
        <DialogTrigger
          className="fixed bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-green-500 text-white shadow-lg transition-all hover:bg-green-600 hover:shadow-xl hover:scale-105 active:scale-95"
          aria-label="问题反馈"
        >
          <MessageCircleQuestion className="h-5 w-5" />
        </DialogTrigger>
        <DialogContent className="sm:max-w-sm">
          <div className="flex flex-col items-center gap-4 py-2">
            <DialogTitle className="text-center text-base font-semibold">
              微信扫码加入交流群
            </DialogTitle>
            <DialogDescription className="text-center text-xs text-muted-foreground">
              获取使用帮助、反馈问题、交流简历优化经验
            </DialogDescription>
            <div className="rounded-xl border bg-muted/30 p-3">
              <Image
                src="/wechat-qr.jpg"
                alt="微信群二维码"
                width={220}
                height={220}
                className="rounded-lg"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              打开微信扫一扫，即可加入群聊
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
