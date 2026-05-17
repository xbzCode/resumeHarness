"use client";

import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  MessageSquare,
  FileText,
  Brain,
  Settings,
  LogOut,
  Menu,
  Plus,
  BookOpen,
  Server,
  Layout,
  Info,
  Wrench,
  Loader2,
  ChevronDown,
  ChevronRight,
  Trash2,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useChatStore, isPendingKey } from "@/store/chat";
import { createAuthApi, type SessionInfo } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AuthGuard } from "@/components/auth-guard";
import { ThemeToggle } from "@/components/theme-toggle";
import { toast } from "sonner";

const NAV_ITEMS = [
  { href: "/chat", label: "对话", icon: MessageSquare },
  { href: "/resumes", label: "简历", icon: FileText },
  { href: "/memory", label: "记忆", icon: Brain },
];

const NAV_ADMIN_ITEMS = [
  { href: "/skills", label: "技能", icon: BookOpen },
  { href: "/tools", label: "工具", icon: Wrench },
  { href: "/mcp", label: "MCP", icon: Server },
  { href: "/templates", label: "模板", icon: Layout },
  { href: "/about", label: "关于", icon: Info },
];

function UserMenu() {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  return (
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button variant="ghost" className="h-8 w-8 rounded-full p-0" />
          }
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">
              {user?.username?.charAt(0).toUpperCase() || "U"}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <div className="px-2 py-1.5">
          <p className="text-sm font-medium">{user?.username}</p>
          <p className="text-xs text-muted-foreground">{user?.email || "未设置邮箱"}</p>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/settings")}>
          <Settings className="mr-2 h-4 w-4" />
          设置
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          退出登录
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** 历史会话列表组件（侧边栏内） */
function SessionList() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const refreshKey = useChatStore((s) => s.refreshKey);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<SessionInfo | null>(null);

  // 初始加载 & token 变化时加载
  useEffect(() => {
    if (token) loadSessions();
  }, [token]);

  // 对话流完成或切换会话时刷新列表
  useEffect(() => {
    if (token && refreshKey > 0) loadSessions();
  }, [refreshKey]);

  async function loadSessions() {
    if (!token) return;
    setLoading(true);
    setLoadError(false);
    try {
      const authApi = createAuthApi(token);
      const data = await authApi<{ sessions: SessionInfo[] }>("/api/sessions");
      setSessions(data.sessions || []);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadSession(sid: string) {
    if (!token) return;
    // 切换会话时：不中止其他会话的 SSE 流，仅切换活跃会话
    const store = useChatStore.getState();
    const existingSession = store.sessions[sid];
    if (existingSession) {
      // 会话已在内存中，直接切换
      store.setActiveSessionId(sid);
      router.push(`/chat?sid=${sid}`);
    } else {
      // 需要从后端加载
      try {
        const authApi = createAuthApi(token);
        const data = await authApi<import("@/lib/api").SessionDetail>(`/api/sessions/${sid}`);
        if (!data.found || !data.messages) return;
        const converted = convertSessionMessages(data.messages);
        store.setMessagesOfSession(sid, converted);
        store.setActiveSessionId(sid);
        router.push(`/chat?sid=${sid}`);
      } catch {
        toast.error("加载会话失败");
      }
    }
  }

  async function handleDeleteSession() {
    if (!token || !deleteTarget) return;
    try {
      const authApi = createAuthApi(token);
      await authApi(`/api/sessions/${deleteTarget.session_id}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((s) => s.session_id !== deleteTarget.session_id));
      // 如果删除的是当前会话，清空聊天
      if (deleteTarget.session_id === activeSessionId) {
        useChatStore.getState().clearSession(deleteTarget.session_id);
        router.replace("/chat");
      }
      toast.success("已删除");
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleteTarget(null);
    }
  }

  function handleNewChat() {
    // 不中止其他会话的流，仅创建新的待定会话
    useChatStore.getState().newPendingSession();
    router.replace("/chat");
  }

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider hover:text-muted-foreground transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        最近对话
      </button>
      {expanded && (
        <>
          {loading ? (
            <div className="flex justify-center py-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground/40" />
            </div>
          ) : loadError ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5">
              <p className="text-[11px] text-destructive/70">获取对话失败</p>
              <button
                type="button"
                onClick={loadSessions}
                className="text-[11px] text-muted-foreground/50 hover:text-foreground underline underline-offset-2 transition-colors"
              >
                重试
              </button>
            </div>
          ) : sessions.length === 0 ? (
            <p className="px-2.5 py-1.5 text-[11px] text-muted-foreground/40">
              暂无历史对话
            </p>
          ) : (
            <div className="max-h-[240px] overflow-y-auto px-1">
              <div className="space-y-0.5">
                {sessions.map((s) => (
                  <div
                    key={s.session_id}
                    className={cn(
                      "group flex items-center gap-1.5 rounded-md px-2 py-1.5 transition-colors cursor-pointer",
                      s.session_id === activeSessionId
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                    )}
                    onClick={() => handleLoadSession(s.session_id)}
                  >
                    <MessageSquare className="h-3 w-3 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[12px] truncate leading-tight">
                        {s.summary || `会话 ${s.session_id.slice(0, 8)}`}
                      </p>
                      <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                        {new Date(s.created_at * 1000).toLocaleDateString()}
                      </p>
                    </div>
                    {/* hover 时显示删除按钮 */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(s);
                      }}
                      className="shrink-0 flex h-5 w-5 items-center justify-center rounded opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10"
                      title="删除对话"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* 删除确认对话框 */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除对话</DialogTitle>
            <DialogDescription>
              确定要删除「{deleteTarget?.summary || deleteTarget?.session_id?.slice(0, 8)}」吗？删除后无法恢复。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteSession}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** 从后端会话消息格式转换为前端 ChatMessage */
function convertSessionMessages(sessionMsgs: import("@/lib/api").SessionMessage[]) {
  const result: { id: string; role: "user" | "assistant" | "system"; content: string; thinking?: string; timestamp: number }[] = [];
  let counter = 0;
  for (const msg of sessionMsgs) {
    if (msg.role !== "user" && msg.role !== "assistant") continue;
    const textParts: string[] = [];
    let thinking = "";
    for (const block of msg.content) {
      if (block.type === "text" && block.text) {
        textParts.push(block.text);
      }
    }
    const reasoning = (msg as unknown as Record<string, unknown>)._reasoning;
    if (typeof reasoning === "string" && reasoning) {
      thinking = reasoning;
    }
    const content = textParts.join("");
    if (!content && !thinking) continue;
    counter += 1;
    result.push({
      id: `msg_${counter}_${Date.now().toString(36)}`,
      role: msg.role as "user" | "assistant",
      content,
      thinking: thinking || undefined,
      timestamp: Date.now(),
    });
  }
  return result;
}

function SidebarContent() {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <Link href="/" className="flex h-11 items-center gap-2 border-b px-4">
        <FileText className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold tracking-tight">Resume Agent</span>
      </Link>

      {/* 新对话按钮 */}
      <div className="p-2">
        <Button
          variant="outline"
          className="w-full gap-2 h-8 text-xs"
          onClick={() => {
            // 不中止其他会话的流，仅创建新的待定会话
            useChatStore.getState().newPendingSession();
            router.replace("/chat");
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          新对话
        </Button>
      </div>

      {/* 导航 + 历史会话 */}
      <ScrollArea className="flex-1 px-2 py-1">
        <nav className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors",
                  active
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}

          {/* 历史会话列表 - 仅在对话页显示 */}
          {pathname.startsWith("/chat") && <SessionList />}

          <div className="pt-3 pb-1 px-2.5">
            <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-wider">系统配置</p>
          </div>
          {NAV_ADMIN_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors",
                  active
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </ScrollArea>

      {/* 底部用户区 */}
      <div className="border-t px-2 py-2">
        <div className="flex items-center gap-1.5 px-2 py-1">
          <UserMenu />
          <span className="flex-1 text-xs text-muted-foreground truncate">
            {user?.username || ""}
          </span>
          <ThemeToggle className="h-6 w-6 shrink-0" />
        </div>
      </div>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      {/* 桌面端侧边栏 */}
      <aside className="hidden w-52 shrink-0 border-r md:block">
        <SidebarContent />
      </aside>

      {/* 移动端侧边栏 */}
      <Sheet>
        <SheetTrigger
          render={
            <Button
              variant="ghost"
              size="icon"
              className="fixed left-3 top-3 z-40 md:hidden"
            />
          }
        >
          <Menu className="h-5 w-5" />
        </SheetTrigger>
        <SheetContent side="left" className="w-52 p-0">
          <SidebarContent />
        </SheetContent>
      </Sheet>

      {/* 主内容区 */}
      <main className="flex-1 overflow-hidden animate-in fade-in-0 duration-200">
        <AuthGuard>{children}</AuthGuard>
      </main>
    </div>
  );
}
