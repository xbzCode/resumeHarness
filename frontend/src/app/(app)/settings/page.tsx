"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Loader2, User, Key, Shield } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi } from "@/lib/api";
import { toast } from "sonner";

const passwordSchema = z
  .object({
    old_password: z.string().min(1, "请输入当前密码"),
    new_password: z.string().min(6, "新密码至少 6 个字符"),
    confirm_password: z.string().min(1, "请确认新密码"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "两次密码不一致",
    path: ["confirm_password"],
  });

type PasswordForm = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const router = useRouter();
  const { token, user, clearAuth } = useAuthStore();
  const [changingPassword, setChangingPassword] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  });

  async function onChangePassword(data: PasswordForm) {
    if (!token) return;
    setChangingPassword(true);
    try {
      const api = createAuthApi(token);
      await api("/api/auth/change-password", {
        method: "POST",
        body: {
          old_password: data.old_password,
          new_password: data.new_password,
        },
      });
      toast.success("密码修改成功，请重新登录");
      clearAuth();
      router.push("/login");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "修改失败";
      toast.error(message);
    } finally {
      setChangingPassword(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center border-b px-4">
        <h2 className="text-sm font-medium">设置</h2>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* 用户信息 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">账户信息</CardTitle>
              </div>
              <CardDescription>你的账户基本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">用户名</span>
                <span className="text-sm font-medium">{user?.username}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">邮箱</span>
                <span className="text-sm">{user?.email || "未设置"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">用户 ID</span>
                <Badge variant="secondary" className="font-mono text-xs">
                  {user?.user_id?.slice(0, 12)}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* 修改密码 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">修改密码</CardTitle>
              </div>
              <CardDescription>修改你的登录密码</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(onChangePassword)} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="old_password">当前密码</Label>
                  <Input
                    id="old_password"
                    type="password"
                    {...register("old_password")}
                  />
                  {errors.old_password && (
                    <p className="text-sm text-destructive">
                      {errors.old_password.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new_password">新密码</Label>
                  <Input
                    id="new_password"
                    type="password"
                    {...register("new_password")}
                  />
                  {errors.new_password && (
                    <p className="text-sm text-destructive">
                      {errors.new_password.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password">确认新密码</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    {...register("confirm_password")}
                  />
                  {errors.confirm_password && (
                    <p className="text-sm text-destructive">
                      {errors.confirm_password.message}
                    </p>
                  )}
                </div>
                <Button type="submit" disabled={changingPassword}>
                  {changingPassword && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  修改密码
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* 关于 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">关于</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>Resume Agent — 智能简历助手</p>
                <p>基于 AI 的简历优化工具</p>
                <p>版本 0.2.0</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
