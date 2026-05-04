"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Layout,
  RefreshCw,
  Palette,
  Building2,
  Check,
  FileText,
  Layers,
  Ruler,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

interface TemplateInfo {
  name: string;
  found: boolean;
  version?: string;
  display_name?: string;
  description?: string;
  author?: string;
  layout?: string;
  color_scheme?: {
    primary?: string;
    accent?: string;
    background?: string;
  };
  recommended_industries?: string[];
  required_fields?: string[];
  optional_fields?: string[];
  supports_dark_mode?: boolean;
  page_size?: string;
  preview?: string;
  has_html?: boolean;
  has_preview?: boolean;
}

interface UserSettings {
  default_template: string;
  language_style: string;
  output_language: string;
  auto_save_resume: boolean;
}

// ---------------------------------------------------------------------------
// 布局类型映射
// ---------------------------------------------------------------------------

const LAYOUT_LABELS: Record<string, string> = {
  "single-column": "单栏",
  "two-column": "双栏",
  card: "卡片式",
};

// ---------------------------------------------------------------------------
// 颜色方案预览
// ---------------------------------------------------------------------------

function ColorSchemePreview({ scheme }: { scheme?: TemplateInfo["color_scheme"] }) {
  if (!scheme) return null;
  return (
    <div className="flex items-center gap-2">
      {scheme.primary && (
        <div className="flex items-center gap-1">
          <div
            className="h-4 w-4 rounded-full border"
            style={{ backgroundColor: scheme.primary }}
          />
          <span className="text-[10px] text-muted-foreground">主色</span>
        </div>
      )}
      {scheme.accent && (
        <div className="flex items-center gap-1">
          <div
            className="h-4 w-4 rounded-full border"
            style={{ backgroundColor: scheme.accent }}
          />
          <span className="text-[10px] text-muted-foreground">强调</span>
        </div>
      )}
      {scheme.background && (
        <div className="flex items-center gap-1">
          <div
            className="h-4 w-4 rounded-full border"
            style={{ backgroundColor: scheme.background }}
          />
          <span className="text-[10px] text-muted-foreground">背景</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 模板卡片
// ---------------------------------------------------------------------------

function TemplateCard({
  template,
  isSelected,
  onSelect,
}: {
  template: TemplateInfo;
  isSelected: boolean;
  onSelect: (name: string) => void;
}) {
  const colorScheme = template.color_scheme;

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md",
        isSelected && "ring-2 ring-primary"
      )}
      onClick={() => onSelect(template.name)}
    >
      {/* 模板视觉预览（基于 color_scheme 模拟） */}
      <div
        className="relative h-32 overflow-hidden rounded-t-lg"
        style={{ backgroundColor: colorScheme?.background || "#ffffff" }}
      >
        {template.layout === "two-column" ? (
          // 双栏布局模拟
          <div className="flex h-full">
            <div
              className="w-1/3 p-3"
              style={{ backgroundColor: colorScheme?.primary || "#1e293b" }}
            >
              <div className="space-y-2">
                <div className="h-2 w-8 rounded bg-white/30" />
                <div className="h-2 w-12 rounded bg-white/20" />
                <div className="mt-3 h-2 w-10 rounded bg-white/15" />
                <div className="h-2 w-10 rounded bg-white/15" />
              </div>
            </div>
            <div className="flex-1 p-3">
              <div className="space-y-2">
                <div
                  className="h-2.5 w-16 rounded"
                  style={{ backgroundColor: colorScheme?.primary || "#1e293b", opacity: 0.6 }}
                />
                <div className="h-1.5 w-full rounded bg-gray-200" />
                <div className="h-1.5 w-4/5 rounded bg-gray-200" />
                <div className="mt-3 h-1.5 w-12 rounded"
                  style={{ backgroundColor: colorScheme?.accent || "#3b82f6", opacity: 0.5 }}
                />
                <div className="h-1.5 w-full rounded bg-gray-100" />
                <div className="h-1.5 w-3/4 rounded bg-gray-100" />
              </div>
            </div>
          </div>
        ) : template.layout === "card" ? (
          // 卡片式布局模拟
          <div className="p-3">
            <div
              className="h-6 rounded-t-lg"
              style={{
                background: `linear-gradient(135deg, ${colorScheme?.primary || "#6366f1"}, ${colorScheme?.accent || "#8b5cf6"})`,
              }}
            />
            <div className="mt-2 space-y-1.5">
              <div className="h-1.5 w-14 rounded bg-gray-200" />
              <div className="h-1.5 w-full rounded bg-gray-100" />
              <div className="flex gap-1.5 mt-2">
                <div className="h-4 w-8 rounded-full bg-gray-100" />
                <div className="h-4 w-10 rounded-full bg-gray-100" />
                <div className="h-4 w-8 rounded-full bg-gray-100" />
              </div>
            </div>
          </div>
        ) : (
          // 单栏布局模拟
          <div className="p-3">
            <div className="space-y-2 text-center">
              <div
                className="mx-auto h-2.5 w-16 rounded"
                style={{ backgroundColor: colorScheme?.primary || "#1e293b", opacity: 0.6 }}
              />
              <div className="mx-auto h-0.5 w-20 rounded"
                style={{ backgroundColor: colorScheme?.accent || "#3b82f6" }}
              />
              <div className="mt-3 space-y-1.5 text-left">
                <div className="h-1.5 w-full rounded bg-gray-200" />
                <div className="h-1.5 w-4/5 rounded bg-gray-200" />
                <div className="h-1.5 w-full rounded bg-gray-100" />
              </div>
            </div>
          </div>
        )}

        {/* 选中标记 */}
        {isSelected && (
          <div className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Check className="h-3 w-3" />
          </div>
        )}
      </div>

      <CardHeader className="pb-2 pt-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm font-medium">
              {template.display_name || template.name}
            </CardTitle>
            {template.description && (
              <CardDescription className="text-xs mt-1 line-clamp-2">
                {template.description}
              </CardDescription>
            )}
          </div>
          <div className="flex items-center gap-1">
            {template.layout && (
              <Badge variant="outline" className="text-[10px] gap-0.5">
                <Layers className="h-2.5 w-2.5" />
                {LAYOUT_LABELS[template.layout] || template.layout}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0 space-y-2">
        {/* 颜色方案 */}
        {colorScheme && <ColorSchemePreview scheme={colorScheme} />}

        {/* 推荐行业 */}
        {template.recommended_industries && template.recommended_industries.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            <Building2 className="h-3 w-3 text-muted-foreground shrink-0" />
            {template.recommended_industries.slice(0, 4).map((ind) => (
              <Badge key={ind} variant="secondary" className="text-[10px] px-1.5 py-0">
                {ind}
              </Badge>
            ))}
          </div>
        )}

        {/* 元信息 */}
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          {template.author && (
            <span>{template.author}</span>
          )}
          {template.page_size && (
            <span className="flex items-center gap-0.5">
              <Ruler className="h-2.5 w-2.5" />
              {template.page_size}
            </span>
          )}
          {template.version && <span>v{template.version}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// 主页面
// ---------------------------------------------------------------------------

export default function TemplatesPage() {
  const { token } = useAuthStore();
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    if (!token) return;
    setLoading(true);
    try {
      const api = createAuthApi(token);
      const [templatesData, settingsData] = await Promise.all([
        api<{ templates: TemplateInfo[] }>("/api/resume/templates"),
        api<UserSettings>("/api/settings").catch(() => null),
      ]);
      setTemplates(templatesData.templates || []);
      if (settingsData) {
        setSettings(settingsData);
      }
    } catch {
      toast.error("加载模板列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectTemplate(templateName: string) {
    if (!token || !settings) return;
    if (settings.default_template === templateName) return;

    setSaving(true);
    try {
      const api = createAuthApi(token);
      const updated = await api<UserSettings>("/api/settings", {
        method: "PUT",
        body: { default_template: templateName },
      });
      setSettings(updated);
      toast.success(`已将默认模板设为「${templates.find(t => t.name === templateName)?.display_name || templateName}」`);
    } catch {
      toast.error("设置默认模板失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Layout className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-medium">模板配置</h2>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{templates.length} 个模板</Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={loading}
            className="gap-1"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            刷新
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-4xl">
          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-64" />
              ))}
            </div>
          ) : templates.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <Layout className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold">暂无模板</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  系统中暂无已注册的简历模板
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="mb-4 text-xs text-muted-foreground">
                点击模板卡片可将其设为默认模板。默认模板在生成简历时自动使用，也可在生成后切换。
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {templates.map((template) => (
                  <TemplateCard
                    key={template.name}
                    template={template}
                    isSelected={settings?.default_template === template.name}
                    onSelect={handleSelectTemplate}
                  />
                ))}
              </div>

              {/* 当前设置 */}
              {settings && (
                <>
                  <Separator className="my-6" />
                  <Card>
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <Palette className="h-5 w-5 text-primary" />
                        <CardTitle className="text-sm">当前模板设置</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">默认模板</span>
                          <Badge variant="default" className="text-xs">
                            {templates.find(t => t.name === settings.default_template)?.display_name || settings.default_template}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
