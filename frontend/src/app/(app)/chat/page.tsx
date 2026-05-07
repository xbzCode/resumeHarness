"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
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
  Plus,
  Copy,
  Check,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { copyToClipboard } from "@/lib/clipboard";
import { useChatStore } from "@/store/chat";
import type { ResumeData } from "@/store/chat";
import { streamChat, downloadFile, createAuthApi } from "@/lib/api";
import { ResumePreview } from "@/components/resume-preview";
import { ResumeScoreCard } from "@/components/resume-score-card";
import { ResumeDiffView } from "@/components/resume-diff-view";
import type { SessionDetail, SessionMessage } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { TEMPLATE_LIST } from "@/components/templates/registry";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

let _idCounter = 0;
function generateId() {
  _idCounter += 1;
  return `msg_${_idCounter}_${Date.now().toString(36)}`;
}

function ToolCallBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
      <Wrench className="h-3 w-3" />
      {name}
    </span>
  );
}

function ThinkingSection({ thinking, streaming }: { thinking: string; streaming?: boolean }) {
  const [open, setOpen] = useState(false);

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
        className="flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-muted-foreground transition-colors"
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
        <div className="mt-1.5 rounded-lg border border-dashed border-border/60 bg-muted/30 p-3 text-[12px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
          {thinking}
        </div>
      )}
    </div>
  );
}

/** 复制消息内容按钮 */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const ok = await copyToClipboard(text);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } else {
      toast.error("复制失败");
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground/40 transition-all hover:bg-muted hover:text-muted-foreground"
      title="复制"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
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

  useEffect(() => {
    if (templateHint) setActiveTemplate(templateHint);
  }, [templateHint]);

  // 收集所有可复制的文本内容
  const copyableText = resumeData
    ? content + (suggestions ? "\n\n" + suggestions : "")
    : content;

  return (
    <div className={cn(
      "group flex gap-3 px-6 py-4 animate-in fade-in-0 slide-in-from-bottom-1 duration-150",
      isUser ? "justify-end" : "justify-start",
    )}>
      {!isUser && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 mt-0.5">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      {/* 内容区：纵向排列气泡 + 复制按钮 */}
      <div className={cn("flex flex-col max-w-[85%] min-w-0")}>
        <div
          className={cn(
            "group/msg relative min-w-0 space-y-2",
            isUser
              ? "rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground"
              : "",
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
            {resumePrefix && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{resumePrefix}</ReactMarkdown>
              </div>
            )}
            {/* 简历预览 - 响应式容器 */}
            <div className="overflow-x-auto rounded-lg border bg-background -mx-1">
              <div className="min-w-[600px]">
                <ResumePreview data={resumeData} template={activeTemplate} />
              </div>
            </div>
            {resumeScore && <ResumeScoreCard score={resumeScore} />}
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
            {/* 操作按钮行 */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="outline" size="sm" className="gap-1 text-xs h-7" />}>
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TEMPLATE_LIST.find(t => t.name === activeTemplate)?.color || "#3b82f6" }} />
                  {TEMPLATE_LIST.find(t => t.name === activeTemplate)?.label || "模板"}
                  <ChevronDown className="h-3 w-3 ml-0.5" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  {TEMPLATE_LIST.map((tpl) => (
                    <DropdownMenuItem
                      key={tpl.name}
                      onClick={() => setActiveTemplate(tpl.name)}
                      className={activeTemplate === tpl.name ? "bg-accent" : ""}
                    >
                      <div className="flex items-center gap-2 w-full">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: tpl.color }} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium">{tpl.label}</div>
                          <div className="text-[10px] text-muted-foreground truncate">{tpl.description}</div>
                        </div>
                        {activeTemplate === tpl.name && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1 text-xs h-7"
                onClick={() => setShowPreview(false)}
              >
                查看原文
              </Button>
              {resumeId && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1 text-xs h-7"
                    onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
                  >
                    <FileText className="h-3 w-3" />
                    详情
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1 text-xs h-7"
                    onClick={() => handleDownloadResume(resumeId)}
                  >
                    <Download className="h-3 w-3" />
                    PDF
                  </Button>
                </>
              )}
            </div>
            {suggestions && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{suggestions}</ReactMarkdown>
              </div>
            )}
          </>
        ) : isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
        {resumeData && !showPreview && (
          <div className="flex gap-1.5 pt-1">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 text-xs h-7"
              onClick={() => setShowPreview(true)}
            >
              简历预览
            </Button>
            {resumeId && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-xs h-7"
                  onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
                >
                  <FileText className="h-3 w-3" />
                  详情
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-xs h-7"
                  onClick={() => handleDownloadResume(resumeId)}
                >
                  <Download className="h-3 w-3" />
                  PDF
                </Button>
              </>
            )}
          </div>
        )}
        {!resumeData && resumeId && (
          <div className="flex gap-1.5 pt-1">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 text-xs h-7"
              onClick={() => window.open(`/resumes/${resumeId}`, "_blank")}
            >
              <FileText className="h-3 w-3" />
              查看简历
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 text-xs h-7"
              onClick={() => handleDownloadResume(resumeId)}
            >
              <Download className="h-3 w-3" />
              PDF
            </Button>
          </div>
        )}
        {/* 助手消息复制按钮 - 左下角 */}
        {!isUser && copyableText && (
          <div className="flex justify-start pt-0.5">
            <CopyButton text={copyableText} />
          </div>
        )}
        </div>
        {/* 用户消息复制按钮 - 气泡下方右对齐 */}
        {isUser && copyableText && (
          <div className="flex justify-end pt-0.5">
            <CopyButton text={copyableText} />
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary mt-0.5">
          <User className="h-3.5 w-3.5 text-secondary-foreground" />
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
    moveContentToThinking,
    setStreaming,
    setAbortController,
    clearMessages,
    setMessages,
    setResumeIdOnLastMessage,
    setResumeDataOnLastMessage,
    setResumeScoreOnLastMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const sid = searchParams.get("sid");
    if (sid && sid !== sessionId && token) {
      setSessionId(sid);
      if (messages.length === 0) {
        loadSession(sid);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, token]);

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
      router.replace(`/chat?sid=${sid}`, { scroll: false });
    } catch {
      toast.error("加载会话详情失败");
    }
  }

  const handleSSEEvent = useCallback(
    (event: MessageEvent) => {
      const data = event.data;
      if (!data || typeof data !== "object") return;

      switch (data.type) {
        case "session_started":
          setSessionId(data.session_id);
          router.replace(`/chat?sid=${data.session_id}`, { scroll: false });
          break;
        case "thinking_delta":
          appendToLastMessageThinking(data.text || "");
          break;
        case "content_to_thinking":
          moveContentToThinking();
          break;
        case "text_delta":
          appendToLastMessage(data.text || "");
          break;
        case "tool_execution_started":
          appendToLastMessage(`\n> 🔧 调用工具: ${data.tool_name}\n`);
          break;
        case "tool_execution_completed":
          appendToLastMessage(`> ✅ ${data.tool_name} 完成${data.is_error ? "（出错）" : ""}\n`);
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
    [appendToLastMessage, appendToLastMessageThinking, moveContentToThinking, setResumeIdOnLastMessage, setResumeDataOnLastMessage, setResumeScoreOnLastMessage, setSessionId],
  );

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

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [input]);

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-11 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {sessionId ? `${sessionId.slice(0, 8)}` : "新对话"}
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleNewChat} className="gap-1 text-xs h-7">
          <Plus className="h-3.5 w-3.5" />
          新对话
        </Button>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-5 py-20 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/5">
              <FileText className="h-7 w-7 text-primary/60" />
            </div>
            <div>
              <h3 className="text-base font-medium">Resume Agent</h3>
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
                  className="text-xs h-8"
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
          <div className="py-2">
            {messages.map((msg, idx) => {
              const isLastAssistantStreaming =
                msg.role === "assistant" &&
                idx === messages.length - 1 &&
                isStreaming;
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
              <div className="flex gap-3 px-6 py-4">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="flex items-center gap-2 rounded-2xl bg-muted px-4 py-2.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">思考中…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t px-4 py-3">
        <div className="mx-auto flex max-w-3xl gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息…"
            className="min-h-[40px] max-h-[200px] resize-none rounded-xl text-sm"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button variant="destructive" size="icon" onClick={handleStop} className="shrink-0 rounded-xl h-10 w-10">
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!input.trim()}
              className="shrink-0 rounded-xl h-10 w-10"
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>
        <p className="mt-1.5 text-center text-[11px] text-muted-foreground/50">
          Enter 发送 · Shift+Enter 换行
        </p>
      </div>
    </div>
  );
}
