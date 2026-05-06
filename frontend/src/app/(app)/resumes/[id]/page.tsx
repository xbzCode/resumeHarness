"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ArrowLeft, Download, Trash2, FileText, Eye, Code, Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, downloadFile, fetchText, fetchJson } from "@/lib/api";
import { ResumePreview } from "@/components/resume-preview";
import type { ResumeData } from "@/store/chat";
import { toast } from "sonner";

/** 后端 /api/resume/{id}/data 返回的结构 */
interface ResumeDataResponse {
  resume_id: string;
  data: ResumeData;
  available_templates: string[];
}

export default function ResumeDetailPage() {
  const router = useRouter();
  const params = useParams();
  const resumeId = params.id as string;
  const { token } = useAuthStore();
  const [resumeData, setResumeData] = useState<ResumeData | null>(null);
  const [markdownContent, setMarkdownContent] = useState<string | null>(null);
  const [markdownLoading, setMarkdownLoading] = useState(false);
  const [activeTemplate, setActiveTemplate] = useState("professional");
  const [loading, setLoading] = useState(true);
  const [showDelete, setShowDelete] = useState(false);
  const [viewMode, setViewMode] = useState<"preview" | "markdown">("preview");

  useEffect(() => {
    loadResume();
  }, [resumeId]);

  async function loadResume() {
    if (!token) return;
    try {
      // 优先加载结构化数据用于预览
      const dataRes = await fetchJson<ResumeDataResponse>(token, `/api/resume/${resumeId}/data`);
      setResumeData(dataRes.data);
      setActiveTemplate(dataRes.available_templates?.[0] || "professional");
    } catch {
      // 结构化数据加载失败时降级为 Markdown
      try {
        const text = await fetchText(token, `/api/resume/${resumeId}/download?format=markdown`);
        setMarkdownContent(text);
        setViewMode("markdown");
      } catch {
        toast.error("加载简历失败");
      }
    } finally {
      setLoading(false);
    }
  }

  /** 切换到原文视图时懒加载 Markdown */
  async function handleViewMarkdown() {
    setViewMode("markdown");
    if (markdownContent !== null) return; // 已加载过
    if (!token) return;
    setMarkdownLoading(true);
    try {
      const text = await fetchText(token, `/api/resume/${resumeId}/download?format=markdown`);
      setMarkdownContent(text);
    } catch {
      setMarkdownContent("");
      toast.error("加载原文失败");
    } finally {
      setMarkdownLoading(false);
    }
  }

  async function handleDownload() {
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

  async function handleDownloadMd() {
    if (!token) return;
    let content = markdownContent;
    if (!content) {
      try {
        content = await fetchText(token, `/api/resume/${resumeId}/download?format=markdown`);
      } catch {
        toast.error("下载失败");
        return;
      }
    }
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resume_${resumeId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDelete() {
    if (!token) return;
    try {
      const api = createAuthApi(token);
      await api(`/api/resume/${resumeId}`, { method: "DELETE" });
      toast.success("已删除");
      router.push("/resumes");
    } catch {
      toast.error("删除失败");
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">简历 {resumeId.slice(0, 12)}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* 视图切换 */}
          <div className="flex gap-1">
            <Button
              variant={viewMode === "preview" ? "default" : "outline"}
              size="sm"
              className="gap-1"
              onClick={() => setViewMode("preview")}
            >
              <Eye className="h-3 w-3" />
              预览
            </Button>
            <Button
              variant={viewMode === "markdown" ? "default" : "outline"}
              size="sm"
              className="gap-1"
              onClick={handleViewMarkdown}
            >
              <Code className="h-3 w-3" />
              原文
            </Button>
          </div>
          {/* 模板切换（仅预览模式） */}
          {resumeData && viewMode === "preview" && (
            <div className="flex gap-1">
              {(["professional", "academic", "creative"] as const).map((tpl) => (
                <Button
                  key={tpl}
                  variant={activeTemplate === tpl ? "secondary" : "ghost"}
                  size="sm"
                  className="text-xs"
                  onClick={() => setActiveTemplate(tpl)}
                >
                  {tpl === "professional" ? "商务" : tpl === "academic" ? "学术" : "创意"}
                </Button>
              ))}
            </div>
          )}
          <Separator orientation="vertical" className="h-6" />
          <Button variant="outline" size="sm" className="gap-1" onClick={handleDownloadMd}>
            <FileText className="h-3 w-3" />
            Markdown
          </Button>
          <Button size="sm" className="gap-1" onClick={handleDownload}>
            <Download className="h-3 w-3" />
            PDF
          </Button>
          <Dialog open={showDelete} onOpenChange={setShowDelete}>
            <DialogTrigger
              render={
                <Button variant="ghost" size="icon" className="text-destructive" />
              }
            >
              <Trash2 className="h-4 w-4" />
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>确认删除</DialogTitle>
                <DialogDescription>删除后无法恢复，确定要删除这份简历吗？</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDelete(false)}>
                  取消
                </Button>
                <Button variant="destructive" onClick={handleDelete}>
                  删除
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        ) : viewMode === "preview" && resumeData ? (
          <div className="mx-auto max-w-4xl">
            <ResumePreview data={resumeData} template={activeTemplate} />
          </div>
        ) : viewMode === "markdown" ? (
          markdownLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">加载原文…</span>
            </div>
          ) : markdownContent ? (
            <div className="mx-auto max-w-3xl">
              <article className="prose prose-slate max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {markdownContent}
                </ReactMarkdown>
              </article>
            </div>
          ) : (
            <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
              无法加载 Markdown 原文
            </div>
          )
        ) : (
          <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
            无法加载简历数据
          </div>
        )}
      </div>
    </div>
  );
}
