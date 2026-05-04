"use client";

import { useState, useEffect } from "react";
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
import { Loader2, User, Key, Shield, FileText } from "lucide-react";
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

interface UserSettings {
  default_template: string;
  language_style: string;
  output_language: string;
  auto_save_resume: boolean;
}

const TEMPLATE_OPTIONS = [
  { value: "professional", label: "简洁商务", desc: "双栏侧边栏，适用于互联网/科技" },
  { value: "academic", label: "学术风", desc: "传统单栏，教育背景优先" },
  { value: "creative", label: "创意排版", desc: "卡片式布局，适用于设计/市场" },
];

const STYLE_OPTIONS = [
  { value: "professional", label: "专业正式" },
  { value: "casual", label: "轻松自然" },
  { value: "academic", label: "学术严谨" },
];

const LANG_OPTIONS = [
  { value: "zh-CN", label: "中文" },
  { value: "en-US", label: "英文" },
];

export default function SettingsPage() {
  const router = useRouter();
  const { token, user, clearAuth } = useAuthStore();
  const [changingPassword, setChangingPassword] = useState(false);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  });

  // 加载用户配置
  useEffect(() => {
    if (!token) return;
    const api = createAuthApi(token);
    api("/api/settings")
      .then((data) => setSettings(data as UserSettings))
      .catch(() => {});
  }, [token]);

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

  async function onSaveSettings() {
    if (!token || !settings) return;
    setSavingSettings(true);
    try {
      const api = createAuthApi(token);
      const updated = await api("/api/settings", {
        method: "PUT",
        body: settings,
      });
      setSettings(updated as UserSettings);
      toast.success("偏好设置已保存");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "保存失败";
      toast.error(message);
    } finally {
      setSavingSettings(false);
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

          {/* 简历偏好 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">简历偏好</CardTitle>
              </div>
              <CardDescription>自定义简历生成的默认设置</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* 默认模板 */}
              <div className="space-y-2">
                <Label className="text-sm">默认模板</Label>
                <div className="grid gap-2">
                  {TEMPLATE_OPTIONS.map((opt) => (
                    <label
                      key={opt.value}
                      className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                        settings?.default_template === opt.value
                          ? "border-primary bg-primary/5"
                          : "border-border hover:bg-muted/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="default_template"
                        value={opt.value}
                        checked={settings?.default_template === opt.value}
                        onChange={() =>
                          settings && setSettings({ ...settings, default_template: opt.value })
                        }
                        className="accent-primary"
                      />
                      <div>
                        <div className="text-sm font-medium">{opt.label}</div>
                        <div className="text-xs text-muted-foreground">{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <Separator />

              {/* 语言风格 */}
              <div className="space-y-2">
                <Label className="text-sm">语言风格</Label>
                <div className="flex gap-2">
                  {STYLE_OPTIONS.map((opt) => (
                    <Button
                      key={opt.value}
                      variant={settings?.language_style === opt.value ? "default" : "outline"}
                      size="sm"
                      onClick={() =>
                        settings && setSettings({ ...settings, language_style: opt.value })
                      }
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>
              </div>

              <Separator />

              {/* 输出语言 */}
              <div className="space-y-2">
                <Label className="text-sm">输出语言</Label>
                <div className="flex gap-2">
                  {LANG_OPTIONS.map((opt) => (
                    <Button
                      key={opt.value}
                      variant={settings?.output_language === opt.value ? "default" : "outline"}
                      size="sm"
                      onClick={() =>
                        settings && setSettings({ ...settings, output_language: opt.value })
                      }
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>
              </div>

              <Separator />

              {/* 自动保存 */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">自动保存简历</div>
                  <div className="text-xs text-muted-foreground">生成简历后自动保存快照</div>
                </div>
                <Button
                  variant={settings?.auto_save_resume !== false ? "default" : "outline"}
                  size="sm"
                  onClick={() =>
                    settings &&
                    setSettings({ ...settings, auto_save_resume: !settings.auto_save_resume })
                  }
                >
                  {settings?.auto_save_resume !== false ? "已开启" : "已关闭"}
                </Button>
              </div>

              <Button onClick={onSaveSettings} disabled={savingSettings} className="w-full">
                {savingSettings && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                保存偏好
              </Button>
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
