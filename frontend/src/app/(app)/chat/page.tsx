"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Send,
  Square,
  FileText,
  Download,
  Loader2,
  Wrench,
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  Brain,
  History,
  Plus,
  MessageSquare,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useChatStore } from "@/store/chat";
import type { ResumeData } from "@/store/chat";
import { streamChat, downloadFile, createAuthApi } from "@/lib/api";
import { ResumePreview } from "@/components/resume-preview";
import { ResumeScoreCard } from "@/components/resume-score-card";
import { ResumeDiffView } from "@/components/resume-diff-view";
import type { SessionInfo, SessionDetail, SessionMessage } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

let _idCounter = 0;
function generateId() {
  _idCounter += 1;
  return `msg_${_idCounter}_${Date.now().toString(36)}`;
}

function ToolCallBadge({ name }: { name: string }) {
  return (
    <Badge variant="secondary" className="gap-1 text-xs">
      <Wrench className="h-3 w-3" />
      {name}
    </Badge>
  );
}

function ThinkingSection({ thinking, streaming }: { thinking: string; streaming?: boolean }) {
  const [open, setOpen] = useState(false);

  // 流式传输中有思考内容时自动展开
  useEffect(() => {
    if (streaming && thinking) {
      setOpen(true);
    }
  }, [streaming, thinking]);

  if (!thinking) return null;

  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <Brain className="h-3 w-3" />
        思考过程
        {streaming && (
          <Loader2 className="h-3 w-3 animate-spin" />
        )}
      </button>
      {open && (
        <div className="mt-1 rounded-md border border-dashed border-muted-foreground/30 bg-background/50 p-3 text-xs text-muted-foreground whitespace-pre-wrap">
          {thinking}
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  role,
  content,
  thinking,
  toolCalls,
  resumeId,
  resumeData,
  templateHint,
  suggestions,
  resumePrefix,
  resumeScore,
  prevResumeContent,
  isStreaming,
}: {
  role: "user" | "assistant" | "system";
  content: string;
  thinking?: string;
  toolCalls?: { name: string; args: string; result?: string }[];
  resumeId?: string;
  resumeData?: ResumeData;
  templateHint?: string;
  suggestions?: string;
  resumePrefix?: string;
  resumeScore?: import("@/store/chat").ResumeScoreData;
  prevResumeContent?: string;
  isStreaming?: boolean;
}) {
  const isUser = role === "user";
  const [showPreview, setShowPreview] = useState(true);
  const [activeTemplate, setActiveTemplate] = useState(templateHint || "professional");

  // 当 templateHint 变化时同步
  useEffect(() => {
    if (templateHint) setActiveTemplate(templateHint);
  }, [templateHint]);

  return (
    <div className={cn("flex gap-3 px-4 py-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[80%] space-y-2 rounded-lg px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted",
        )}
      >
        {!isUser && <ThinkingSection thinking={thinking || ""} streaming={isStreaming} />}
        {toolCalls && toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {toolCalls.map((tc, i) => (
              <ToolCallBadge key={i} name={tc.name} />
            ))}
          </div>
        )}
        {resumeData && showPreview ? (
          <>
            {/* 前缀内容（标记前的引导语等） */}
            {resumePrefix && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{resumePrefix}</ReactMarkdown>
              </div>
            )}
            {/* 简历预览组件 */}
            <div className="space-y-2">
              <ResumePreview data={resumeData} template={activeTemplate} />
              {/* 简历评分卡片 */}
              {resumeScore && <ResumeScoreCard score={resumeScore} />}
              {/* 多轮优化差异对比 */}
              {prevResumeContent && resumeData && (
                <ResumeDiffView
                  oldContent={prevResumeContent}
                  newContent={(() => {
                    const parts: string[] = [];
                    parts.push(`# ${resumeData.name}`);
                    const cp = [resumeData.contact.email, resumeData.contact.phone, resumeData.contact.location].filter(Boolean);
                    if (cp.length > 0) parts.push(cp.join(" | "));
                    if (resumeData.summary) { parts.push(""); parts.push("## 个人简介"); parts.push(resumeData.summary); }
                    if (resumeData.experience.length > 0) {
                      parts.push(""); parts.push("## 工作经历");
                      for (const exp of resumeData.experience) {
                        parts.push(`### ${exp.title} - ${exp.company}（${exp.period}）`);
                        for (const h of exp.highlights) parts.push(`- ${h}`);
                      }
                    }
                    return parts.join("\n");
                  })()}
                />
              )}
              {/* 模板切换 + 操作按钮 */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex gap-1 mr-2">
                  {(["professional", "academic", "creative"] as const).map((tpl) => (
                    <Button
                      key={tpl}
                      variant={activeTemplate === tpl ? "default" : "outline"}
                      size="sm"
                      className="gap-1 text-xs"
                      onClick={() => setActiveTemplate(tpl)}
                    >
                      {tpl === "professional" ? "商务" : tpl === "academic" ? "学术" : "创意"}
                    </Button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => setShowPreview(false)}
                >
                  查看原文
                </Button>
                {resumeId && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
                    >
                      <FileText className="h-3 w-3" />
                      详情
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => handleDownloadResume(resumeId)}
                    >
                      <Download className="h-3 w-3" />
                      下载 PDF
                    </Button>
                  </>
                )}
              </div>
            </div>
            {/* 后缀内容（优化建议等） */}
            {suggestions && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{suggestions}</ReactMarkdown>
              </div>
            )}
          </>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
        {resumeData && !showPreview && (
          <div className="flex gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => setShowPreview(true)}
            >
              简历预览
            </Button>
            {resumeId && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
                >
                  <FileText className="h-3 w-3" />
                  详情
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => handleDownloadResume(resumeId)}
                >
                  <Download className="h-3 w-3" />
                  下载 PDF
                </Button>
              </>
            )}
          </div>
        )}
        {!resumeData && resumeId && (
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
            >
              <FileText className="h-3 w-3" />
              查看简历
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1"
              onClick={() => handleDownloadResume(resumeId)}
            >
              <Download className="h-3 w-3" />
              下载 PDF
            </Button>
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
          <User className="h-4 w-4 text-secondary-foreground" />
        </div>
      )}
    </div>
  );
}

async function handleDownloadResume(resumeId: string) {
  const token = useAuthStore.getState().token;
  if (!token) return;
  try {
    const blob = await downloadFile(token, `/api/resume/${resumeId}/download?format=pdf`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resume_${resumeId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    toast.error("下载失败");
  }
}

/** 从后端会话消息格式转换为前端 ChatMessage */
function convertSessionMessages(sessionMsgs: SessionMessage[]) {
  const result: { id: string; role: "user" | "assistant" | "system"; content: string; thinking?: string; timestamp: number }[] = [];
  for (const msg of sessionMsgs) {
    if (msg.role !== "user" && msg.role !== "assistant") continue;
    const textParts: string[] = [];
    const toolNames: string[] = [];
    let thinking = "";
    for (const block of msg.content) {
      if (block.type === "text" && block.text) {
        textParts.push(block.text);
      } else if (block.type === "tool_use" && block.name) {
        toolNames.push(block.name);
      } else if (block.type === "tool_result") {
        // tool results 不单独显示
      }
    }
    // 尝试提取 reasoning（如果有 _reasoning 字段）
    const reasoning = (msg as Record<string, unknown>)._reasoning;
    if (typeof reasoning === "string" && reasoning) {
      thinking = reasoning;
    }
    const content = textParts.join("");
    if (!content && !thinking && toolNames.length === 0) continue;
    result.push({
      id: generateId(),
      role: msg.role as "user" | "assistant",
      content,
      thinking: thinking || undefined,
      timestamp: Date.now(),
    });
  }
  return result;
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token } = useAuthStore();
  const {
    sessionId,
    messages,
    isStreaming,
    setSessionId,
    addMessage,
    appendToLastMessage,
    appendToLastMessageThinking,
    setStreaming,
    setAbortController,
    clearMessages,
    setMessages,
    setResumeIdOnLastMessage,
    setResumeDataOnLastMessage,
    setResumeScoreOnLastMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 从 URL 参数恢复会话
  useEffect(() => {
    const sid = searchParams.get("sid");
    if (sid && sid !== sessionId && token) {
      setSessionId(sid);
      // 如果当前没有消息，加载该会话的历史消息
      if (messages.length === 0) {
        loadSession(sid);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, token]);

  // 加载历史会话列表
  async function loadSessions() {
    if (!token) return;
    setLoadingSessions(true);
    try {
      const authApi = createAuthApi(token);
      const data = await authApi<{ sessions: SessionInfo[] }>("/api/sessions");
      setSessions(data.sessions || []);
    } catch {
      toast.error("加载历史会话失败");
    } finally {
      setLoadingSessions(false);
    }
  }

  // 打开历史面板时加载
  function handleOpenSheet(open: boolean) {
    setSheetOpen(open);
    if (open) {
      loadSessions();
    }
  }

  // 加载某个历史会话
  async function loadSession(sid: string) {
    if (!token) return;
    try {
      const authApi = createAuthApi(token);
      const data = await authApi<SessionDetail>(`/api/sessions/${sid}`);
      if (!data.found || !data.messages) {
        toast.error("会话不存在");
        return;
      }
      const converted = convertSessionMessages(data.messages);
      setSessionId(sid);
      setMessages(converted);
      setSheetOpen(false);
      router.replace(`/chat?sid=${sid}`, { scroll: false });
    } catch {
      toast.error("加载会话详情失败");
    }
  }

  // 处理 SSE 事件
  const handleSSEEvent = useCallback(
    (event: MessageEvent) => {
      const data = event.data;
      if (!data || typeof data !== "object") return;

      switch (data.type) {
        case "session_started":
          setSessionId(data.session_id);
          // 更新 URL 为 /chat?sid=xxx（不产生额外历史记录）
          router.replace(`/chat?sid=${data.session_id}`, { scroll: false });
          break;
        case "thinking_delta":
          appendToLastMessageThinking(data.text || "");
          break;
        case "text_delta":
          appendToLastMessage(data.text || "");
          break;
        case "tool_execution_started":
          appendToLastMessage(
            `\n> 🔧 调用工具: ${data.tool_name}\n`,
          );
          break;
        case "tool_execution_completed":
          appendToLastMessage(
            `> ✅ ${data.tool_name} 完成${data.is_error ? "（出错）" : ""}\n`,
          );
          break;
        case "status":
          appendToLastMessage(`\n> 📌 ${data.message}\n`);
          break;
        case "resume_generated":
          setResumeIdOnLastMessage(data.resume_id);
          toast.success("简历已生成！");
          break;
        case "resume_data":
          if (data.resume_id && data.data) {
            setResumeDataOnLastMessage(
              data.resume_id,
              data.data,
              data.template_hint || "professional",
              data.suggestions || "",
              data.resume_prefix || "",
            );
          }
          break;
        case "resume_score":
          if (data.overall_score !== undefined) {
            setResumeScoreOnLastMessage({
              overall_score: data.overall_score,
              dimensions: data.dimensions || {},
              suggestions: data.suggestions || [],
              jd_keywords_matched: data.jd_keywords_matched,
              jd_keywords_missing: data.jd_keywords_missing,
            });
          }
          break;
        case "assistant_turn_complete":
          break;
        case "ping":
          break;
        case "error":
          appendToLastMessage(`\n> ⚠️ 错误: ${data.message}\n`);
          break;
      }
    },
    [appendToLastMessage, appendToLastMessageThinking, setResumeIdOnLastMessage, setResumeDataOnLastMessage, setResumeScoreOnLastMessage, setSessionId],
  );

  // 发送消息
  async function handleSend() {
    const prompt = input.trim();
    if (!prompt || isStreaming || !token) return;

    setInput("");

    addMessage({
      id: generateId(),
      role: "user",
      content: prompt,
      timestamp: Date.now(),
    });

    addMessage({
      id: generateId(),
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    });

    setStreaming(true);

    streamChat(
      token,
      { prompt, session_id: sessionId || undefined },
      handleSSEEvent,
      (err) => {
        toast.error(`对话出错: ${err.message}`);
        setStreaming(false);
      },
      () => {
        setStreaming(false);
      },
    ).then((abort) => {
      setAbortController(abort);
    });
  }

  function handleStop() {
    useChatStore.getState().abortController?.();
    setStreaming(false);
    setAbortController(null);
  }

  function handleNewChat() {
    useChatStore.getState().abortController?.();
    clearMessages();
    setStreaming(false);
    setAbortController(null);
    router.replace("/chat", { scroll: false });
  }

  // Enter 发送，Shift+Enter 换行
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // 调整 textarea 高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [input]);

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <h2 className="text-sm font-medium">
          {sessionId ? `会话 ${sessionId.slice(0, 8)}` : "新对话"}
        </h2>
        <div className="flex items-center gap-1">
          {/* 历史会话 */}
          <Sheet open={sheetOpen} onOpenChange={handleOpenSheet}>
            <SheetTrigger
              render={
                <Button variant="ghost" size="sm" className="gap-1" />
              }
            >
              <History className="h-4 w-4" />
              历史
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0">
              <SheetHeader className="border-b px-4 py-3">
                <SheetTitle className="text-sm">历史会话</SheetTitle>
              </SheetHeader>
              <div className="overflow-y-auto p-2" style={{ height: "calc(100% - 52px)" }}>
                {loadingSessions ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : sessions.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    暂无历史会话
                  </div>
                ) : (
                  <div className="space-y-1">
                    {sessions.map((s) => (
                      <button
                        key={s.session_id}
                        type="button"
                        onClick={() => loadSession(s.session_id)}
                        className={cn(
                          "flex w-full items-start gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                          s.session_id === sessionId && "bg-accent",
                        )}
                      >
                        <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium">
                            {s.summary || `会话 ${s.session_id.slice(0, 8)}`}
                          </p>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {s.message_count} 条消息 · {new Date(s.created_at * 1000).toLocaleDateString()}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>
          <Button variant="ghost" size="sm" onClick={handleNewChat} className="gap-1">
            <Plus className="h-4 w-4" />
            新对话
          </Button>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <FileText className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Resume Agent</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                输入你的简历和目标岗位，开始智能优化
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                "帮我优化这份简历，目标岗位是前端工程师",
                "根据这个 JD 调整我的简历",
                "我的简历有哪些可以改进的地方？",
              ].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    setInput(suggestion);
                    textareaRef.current?.focus();
                  }}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-1 py-2">
            {messages.map((msg, idx) => {
              const isLastAssistantStreaming =
                msg.role === "assistant" &&
                idx === messages.length - 1 &&
                isStreaming;
              // 流式传输中，完全空的 assistant 消息由下方的"思考中..."替代，不单独渲染
              if (
                isLastAssistantStreaming &&
                !msg.content &&
                !msg.thinking
              ) {
                return null;
              }
              return (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  thinking={msg.thinking}
                  toolCalls={msg.toolCalls}
                  resumeId={msg.resumeId}
                  resumeData={msg.resumeData}
                  templateHint={msg.templateHint}
                  suggestions={msg.suggestions}
                  resumePrefix={msg.resumePrefix}
                  resumeScore={msg.resumeScore}
                  prevResumeContent={msg.prevResumeContent}
                  isStreaming={isLastAssistantStreaming}
                />
              );
            })}
            {isStreaming && messages[messages.length - 1]?.content === "" && !messages[messages.length - 1]?.thinking && (
              <div className="flex gap-3 px-4 py-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    思考中...
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t p-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
            className="min-h-[44px] max-h-[200px] resize-none"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button variant="destructive" size="icon" onClick={handleStop}>
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
