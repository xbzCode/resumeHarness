"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, type Variants } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText, Loader2, ArrowRight, Sparkles, Zap, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const registerSchema = z
  .object({
    username: z.string().min(3, "用户名至少 3 个字符").max(20, "用户名最多 20 个字符"),
    password: z.string().min(6, "密码至少 6 个字符"),
    confirmPassword: z.string().min(1, "请确认密码"),
    email: z.string().email("请输入有效的邮箱地址").optional().or(z.literal("")),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "两次密码不一致",
    path: ["confirmPassword"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

const fadeRight: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.15, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

const fadeLeft: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.12, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  async function onSubmit(data: RegisterForm) {
    setLoading(true);
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: {
          username: data.username,
          password: data.password,
          email: data.email || undefined,
        },
      });

      toast.success("注册成功，请登录");
      router.push("/login");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "注册失败";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* 左侧装饰区 */}
      <div className="hidden lg:flex lg:w-[45%] items-center justify-center relative overflow-hidden bg-gradient-to-br from-primary/5 via-primary/[0.02] to-transparent">
        {/* 网格背景 */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        {/* 径向光晕 */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_30%,rgba(120,119,198,0.1),transparent)]" />

        <div className="relative z-10 px-12 max-w-sm">
          <motion.div variants={fadeRight} initial="hidden" animate="visible" custom={0}>
            <div className="mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-primary/5 shadow-sm">
              <FileText className="h-8 w-8 text-primary" />
            </div>
          </motion.div>

          <motion.h2
            variants={fadeRight}
            initial="hidden"
            animate="visible"
            custom={1}
            className="text-2xl font-bold tracking-tight text-center"
          >
            Resume Agent
          </motion.h2>

          <motion.p
            variants={fadeRight}
            initial="hidden"
            animate="visible"
            custom={2}
            className="mt-3 text-sm text-muted-foreground text-center leading-relaxed"
          >
            AI 驱动的智能简历优化助手，让简历匹配每一个目标岗位
          </motion.p>

          <motion.div
            variants={fadeRight}
            initial="hidden"
            animate="visible"
            custom={3}
            className="mt-10 space-y-4"
          >
            {[
              { icon: Sparkles, text: "智能分析简历与岗位匹配度" },
              { icon: Zap, text: "一键生成多模板优化简历" },
              { icon: Shield, text: "数据安全隔离，隐私无忧" },
            ].map((item, i) => (
              <motion.div
                key={i}
                variants={fadeRight}
                initial="hidden"
                animate="visible"
                custom={3 + i * 0.5}
                className="flex items-center gap-3 rounded-xl bg-background/60 px-4 py-3 backdrop-blur-sm border border-border/50"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <item.icon className="h-4 w-4 text-primary" />
                </div>
                <span className="text-sm text-muted-foreground">{item.text}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* 右侧表单区 */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <motion.div
          variants={fadeLeft}
          initial="hidden"
          animate="visible"
          custom={0}
          className="w-full max-w-sm"
        >
          {/* 移动端 Logo */}
          <div className="mb-8 text-center lg:hidden">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary/15 to-primary/5">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm font-semibold">Resume Agent</p>
          </div>

          <motion.h1
            variants={fadeLeft}
            initial="hidden"
            animate="visible"
            custom={1}
            className="text-2xl font-bold tracking-tight"
          >
            创建账号
          </motion.h1>
          <motion.p
            variants={fadeLeft}
            initial="hidden"
            animate="visible"
            custom={2}
            className="mt-2 text-sm text-muted-foreground"
          >
            注册后即可免费使用，开始优化你的简历
          </motion.p>

          <motion.form
            variants={fadeLeft}
            initial="hidden"
            animate="visible"
            custom={3}
            onSubmit={handleSubmit(onSubmit)}
            className="mt-8 space-y-5"
          >
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                placeholder="3-20 个字符"
                className="h-10"
                {...register("username")}
              />
              {errors.username && (
                <p className="text-sm text-destructive">{errors.username.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱（选填）</Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                className="h-10"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="至少 6 个字符"
                className="h-10"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认密码</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="再次输入密码"
                className="h-10"
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p className="text-sm text-destructive">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
            <Button type="submit" className="w-full h-10 gap-2" disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              注册
            </Button>
          </motion.form>

          <motion.p
            variants={fadeLeft}
            initial="hidden"
            animate="visible"
            custom={4}
            className="mt-8 text-center text-sm text-muted-foreground"
          >
            已有账号？{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              登录
            </Link>
          </motion.p>
        </motion.div>
      </div>
    </div>
  );
}
