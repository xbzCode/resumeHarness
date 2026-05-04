"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Server,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Wrench,
  Key,
  Plus,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

interface McpToolInfo {
  name: string;
  description: string;
}

interface McpServerStatus {
  url: string;
  connected: boolean;
  tools: McpToolInfo[];
  reason?: string;
}

interface McpStatus {
  initialized: boolean;
  total_servers: number;
  connected_servers: number;
  servers: Record<string, McpServerStatus>;
}

interface McpAuthInfo {
  server_name: string;
  headers: Record<string, string>;
  has_auth: boolean;
}

// ---------------------------------------------------------------------------
// 认证配置对话框
// ---------------------------------------------------------------------------

function AuthConfigDialog({
  serverName,
  onSaved,
}: {
  serverName: string;
  onSaved: () => void;
}) {
  const { token } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [authInfo, setAuthInfo] = useState<McpAuthInfo | null>(null);
  const [headers, setHeaders] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  async function loadAuth() {
    if (!token) return;
    setLoading(true);
    try {
      const api = createAuthApi(token);
      const data = await api<McpAuthInfo>(`/api/mcp/auth/${serverName}`);
      setAuthInfo(data);
      // 展开掩码值，用户需要重新输入才能修改
      setHeaders(data.headers || {});
    } catch {
      setAuthInfo(null);
      setHeaders({});
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!token) return;
    setSaving(true);
    try {
      const api = createAuthApi(token);
      await api(`/api/mcp/auth/${serverName}`, {
        method: "PUT",
        body: { headers },
      });
      toast.success("认证配置已保存");
      onSaved();
      setOpen(false);
    } catch {
      toast.error("保存认证配置失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!token) return;
    try {
      const api = createAuthApi(token);
      await api(`/api/mcp/auth/${serverName}`, { method: "DELETE" });
      toast.success("认证配置已删除");
      setHeaders({});
      setAuthInfo(null);
      onSaved();
      setOpen(false);
    } catch {
      toast.error("删除认证配置失败");
    }
  }

  function addHeader() {
    const key = `header_${Object.keys(headers).length + 1}`;
    setHeaders({ ...headers, [key]: "" });
  }

  function removeHeader(key: string) {
    const newHeaders = { ...headers };
    delete newHeaders[key];
    setHeaders(newHeaders);
  }

  function updateHeaderKey(oldKey: string, newKey: string) {
    const newHeaders: Record<string, string> = {};
    for (const [k, v] of Object.entries(headers)) {
      newHeaders[k === oldKey ? newKey : k] = v;
    }
    setHeaders(newHeaders);
  }

  function updateHeaderValue(key: string, value: string) {
    setHeaders({ ...headers, [key]: value });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (v) loadAuth();
      }}
    >
      <DialogTrigger render={<Button variant="outline" size="sm" className="gap-1" />}>
        <Key className="h-3 w-3" />
        认证配置
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            {serverName} — 认证配置
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
          ) : (
            <>
              <div className="text-xs text-muted-foreground">
                配置调用此 MCP 服务器时使用的 HTTP 请求头（如 Authorization、API Key 等）。
                敏感值已掩码显示，修改时需重新输入完整值。
              </div>

              <div className="space-y-2">
                {Object.entries(headers).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Input
                      value={key}
                      onChange={(e) => updateHeaderKey(key, e.target.value)}
                      placeholder="Header 名称"
                      className="flex-1 text-xs"
                    />
                    <Input
                      value={value}
                      onChange={(e) => updateHeaderValue(key, e.target.value)}
                      placeholder="值"
                      className="flex-1 text-xs"
                      type={key.toLowerCase().includes("auth") ? "password" : "text"}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      onClick={() => removeHeader(key)}
                    >
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>

              <Button variant="outline" size="sm" onClick={addHeader} className="w-full gap-1">
                <Plus className="h-3 w-3" />
                添加 Header
              </Button>

              <Separator />

              <div className="flex gap-2">
                {authInfo?.has_auth && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDelete}
                    className="text-destructive gap-1"
                  >
                    <Trash2 className="h-3 w-3" />
                    删除配置
                  </Button>
                )}
                <div className="flex-1" />
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  {saving ? "保存中..." : "保存配置"}
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// MCP 服务器卡片
// ---------------------------------------------------------------------------

function McpServerCard({
  name,
  status,
  onAuthSaved,
}: {
  name: string;
  status: McpServerStatus;
  onAuthSaved: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg",
                status.connected
                  ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                  : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
              )}
            >
              <Server className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-medium">{name}</CardTitle>
              <div className="flex items-center gap-1 mt-0.5">
                {status.connected ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 text-green-600" />
                    <span className="text-xs text-green-600">已连接</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-3 w-3 text-red-500" />
                    <span className="text-xs text-red-500">
                      {status.reason || "未连接"}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-[10px] gap-1">
              <Wrench className="h-2.5 w-2.5" />
              {status.tools.length} 工具
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        {/* URL */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <ExternalLink className="h-3 w-3" />
          <span className="font-mono truncate">{status.url}</span>
        </div>

        {/* 工具列表 */}
        {status.tools.length > 0 && (
          <div className="space-y-1.5">
            {status.tools.map((tool) => (
              <div
                key={tool.name}
                className="flex items-start gap-2 rounded-md bg-muted/50 px-2.5 py-1.5"
              >
                <Wrench className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-medium">{tool.name}</p>
                  {tool.description && (
                    <p className="text-[10px] text-muted-foreground line-clamp-2">
                      {tool.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <Separator />

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          <AuthConfigDialog serverName={name} onSaved={onAuthSaved} />
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// 主页面
// ---------------------------------------------------------------------------

export default function McpPage() {
  const { token } = useAuthStore();
  const [status, setStatus] = useState<McpStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    if (!token) return;
    setLoading(true);
    try {
      const api = createAuthApi(token);
      const data = await api<McpStatus>("/api/mcp/status");
      setStatus(data);
    } catch {
      toast.error("加载 MCP 状态失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    if (!token) return;
    setRefreshing(true);
    try {
      const api = createAuthApi(token);
      await api("/api/mcp/refresh", { method: "POST" });
      toast.success("MCP 连接已刷新");
      await loadStatus();
    } catch {
      toast.error("刷新 MCP 连接失败");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-medium">MCP 服务管理</h2>
        </div>
        <div className="flex items-center gap-2">
          {status && (
            <>
              <Badge variant="secondary">
                {status.connected_servers}/{status.total_servers} 已连接
              </Badge>
              <Badge
                variant={status.initialized ? "default" : "outline"}
                className="text-xs"
              >
                {status.initialized ? "已初始化" : "未初始化"}
              </Badge>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            className="gap-1"
          >
            <RefreshCw className={cn("h-3 w-3", refreshing && "animate-spin")} />
            刷新连接
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-3xl">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-40" />
              ))}
            </div>
          ) : !status || Object.keys(status.servers).length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <Server className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold">暂无 MCP 服务器</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  系统中暂无已配置的 MCP 服务器
                </p>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {Object.entries(status.servers).map(([name, serverStatus]) => (
                <McpServerCard
                  key={name}
                  name={name}
                  status={serverStatus}
                  onAuthSaved={loadStatus}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
