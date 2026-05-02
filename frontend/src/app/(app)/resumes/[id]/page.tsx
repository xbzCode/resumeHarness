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
import { ArrowLeft, Download, Trash2, FileText } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, downloadFile, fetchText } from "@/lib/api";
import { toast } from "sonner";

export default function ResumeDetailPage() {
  const router = useRouter();
  const params = useParams();
  const resumeId = params.id as string;
  const { token } = useAuthStore();
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    loadResume();
  }, [resumeId]);

  async function loadResume() {
    if (!token) return;
    try {
      const text = await fetchText(token, `/api/resume/${resumeId}/download?format=markdown`);
      setContent(text);
    } catch {
      toast.error("加载简历失败");
    } finally {
      setLoading(false);
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
        <div className="flex gap-2">
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
        ) : (
          <div className="mx-auto max-w-3xl">
            <article className="prose prose-slate max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
