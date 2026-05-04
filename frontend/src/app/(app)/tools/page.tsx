"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Wrench,
  RefreshCw,
  Shield,
  ShieldCheck,
  Server,
  Cpu,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

interface ToolInfo {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  category: string;
  is_read_only: boolean;
  source: "builtin" | "mcp";
}

interface ToolsResponse {
  tools: ToolInfo[];
  total: number;
  categories: Record<string, number>;
}

// ---------------------------------------------------------------------------
// 分类颜色
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  记忆: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  技能: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  网络: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  文件转换: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  邮件发送: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  网络抓取: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200",
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
}

// ---------------------------------------------------------------------------
// 工具 Schema 展示
// ---------------------------------------------------------------------------

function SchemaViewer({ schema }: { schema: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const properties = (schema.properties || {}) as Record<string, { type?: string; description?: string; default?: unknown }>;
  const required = (schema.required || []) as string[];
  const propEntries = Object.entries(properties);

  if (propEntries.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        参数定义 ({propEntries.length})
      </button>
      {expanded && (
        <div className="mt-2 space-y-1.5 rounded-md bg-muted/50 p-2">
          {propEntries.map(([key, prop]) => (
            <div key={key} className="flex items-start gap-2 text-xs">
              <code className="rounded bg-background px-1 py-0.5 font-mono text-primary">
                {key}
              </code>
              <span className="text-muted-foreground">{prop.type || "any"}</span>
              {required.includes(key) && (
                <Badge variant="destructive" className="text-[8px] px-1 py-0 h-4">
                  必填
                </Badge>
              )}
              {prop.description && (
                <span className="text-muted-foreground flex-1">
                  — {prop.description}
                </span>
              )}
              {prop.default !== undefined && (
                <span className="text-muted-foreground">
                  默认: {String(prop.default)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 工具卡片
// ---------------------------------------------------------------------------

function ToolCard({ tool }: { tool: ToolInfo }) {
  return (
    <Card className="transition-all hover:shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {tool.source === "mcp" ? (
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300">
                <Server className="h-3.5 w-3.5" />
              </div>
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                <Cpu className="h-3.5 w-3.5" />
              </div>
            )}
            <div>
              <CardTitle className="text-sm font-mono">{tool.name}</CardTitle>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Badge className={cn("text-[10px]", getCategoryColor(tool.category))}>
                  {tool.category}
                </Badge>
                {tool.source === "mcp" && (
                  <Badge variant="outline" className="text-[10px] gap-0.5">
                    <Server className="h-2.5 w-2.5" />
                    MCP
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {tool.is_read_only ? (
              <div className="flex items-center gap-0.5 text-green-600" title="只读工具">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span className="text-[10px]">只读</span>
              </div>
            ) : (
              <div className="flex items-center gap-0.5 text-amber-600" title="可写工具">
                <Shield className="h-3.5 w-3.5" />
                <span className="text-[10px]">可写</span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-2">
        <p className="text-xs text-muted-foreground">{tool.description}</p>
        <SchemaViewer schema={tool.input_schema} />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// 主页面
// ---------------------------------------------------------------------------

export default function ToolsPage() {
  const { token } = useAuthStore();
  const [data, setData] = useState<ToolsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  const [filterSource, setFilterSource] = useState<"all" | "builtin" | "mcp">("all");

  useEffect(() => {
    loadTools();
  }, []);

  async function loadTools() {
    if (!token) return;
    setLoading(true);
    try {
      const api = createAuthApi(token);
      const result = await api<ToolsResponse>("/api/tools");
      setData(result);
    } catch {
      toast.error("加载工具列表失败");
    } finally {
      setLoading(false);
    }
  }

  const filteredTools = data?.tools.filter((tool) => {
    if (filterCategory && tool.category !== filterCategory) return false;
    if (filterSource !== "all" && tool.source !== filterSource) return false;
    return true;
  }) || [];

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-medium">工具管理</h2>
        </div>
        <div className="flex items-center gap-2">
          {data && (
            <Badge variant="secondary">{data.total} 个工具</Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={loadTools}
            disabled={loading}
            className="gap-1"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            刷新
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-3xl">
          {/* 过滤器 */}
          {data && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">分类</span>
              <Button
                variant={filterCategory === null ? "default" : "outline"}
                size="sm"
                className="h-6 text-[10px]"
                onClick={() => setFilterCategory(null)}
              >
                全部
              </Button>
              {Object.entries(data.categories).map(([cat, count]) => (
                <Button
                  key={cat}
                  variant={filterCategory === cat ? "default" : "outline"}
                  size="sm"
                  className="h-6 text-[10px] gap-1"
                  onClick={() =>
                    setFilterCategory(filterCategory === cat ? null : cat)
                  }
                >
                  {cat}
                  <Badge variant="secondary" className="text-[8px] px-1 h-3.5">
                    {count}
                  </Badge>
                </Button>
              ))}

              <Separator orientation="vertical" className="h-4 mx-1" />

              <span className="text-xs text-muted-foreground">来源</span>
              {(["all", "builtin", "mcp"] as const).map((src) => (
                <Button
                  key={src}
                  variant={filterSource === src ? "default" : "outline"}
                  size="sm"
                  className="h-6 text-[10px]"
                  onClick={() => setFilterSource(src)}
                >
                  {src === "all" ? "全部" : src === "builtin" ? "内置" : "MCP"}
                </Button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : filteredTools.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <Wrench className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold">暂无工具</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {filterCategory || filterSource !== "all"
                    ? "当前筛选条件下没有匹配的工具"
                    : "系统中暂无已注册的工具"}
                </p>
              </div>
            </div>
          ) : (
            <div className="grid gap-3">
              {filteredTools.map((tool) => (
                <ToolCard key={tool.name} tool={tool} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
