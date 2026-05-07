"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { FileText, Download, Trash2, Eye, Clock } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, downloadFile, type ResumeInfo } from "@/lib/api";
import { toast } from "sonner";

export default function ResumesPage() {
  const { token } = useAuthStore();
  const [resumes, setResumes] = useState<ResumeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    loadResumes();
  }, []);

  async function loadResumes() {
    if (!token) return;
    try {
      const api = createAuthApi(token);
      const data = await api<{ resumes: ResumeInfo[] }>("/api/resume");
      setResumes(data.resumes || []);
    } catch {
      toast.error("加载简历列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(resumeId: string) {
    if (!token) return;
    try {
      const api = createAuthApi(token);
      await api(`/api/resume/${resumeId}`, { method: "DELETE" });
      toast.success("已删除");
      setResumes((prev) => prev.filter((r) => r.resume_id !== resumeId));
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleteId(null);
    }
  }

  async function handleDownload(resumeId: string) {
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <h2 className="text-sm font-medium">我的简历</h2>
        <Badge variant="secondary">{resumes.length} 份</Badge>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        ) : resumes.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-semibold">暂无简历</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                在对话中生成简历后会出现在这里
              </p>
            </div>
            <Link href="/chat">
              <Button>开始对话</Button>
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {resumes.map((resume) => (
              <Card key={resume.resume_id} className="group relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <FileText className="h-8 w-8 text-primary" />
                    <Dialog
                      open={deleteId === resume.resume_id}
                      onOpenChange={(open) => setDeleteId(open ? resume.resume_id : null)}
                    >
                      <DialogTrigger
                        render={
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          />
                        }
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>确认删除</DialogTitle>
                          <DialogDescription>
                            删除后无法恢复，确定要删除这份简历吗？
                          </DialogDescription>
                        </DialogHeader>
                        <DialogFooter>
                          <Button
                            variant="outline"
                            onClick={() => setDeleteId(null)}
                          >
                            取消
                          </Button>
                          <Button
                            variant="destructive"
                            onClick={() => handleDelete(resume.resume_id)}
                          >
                            删除
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </div>
                  <CardTitle className="text-sm">
                    {resume.resume_id.slice(0, 12)}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {new Date(resume.created_at * 1000).toLocaleString("zh-CN")}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {(resume.size_bytes / 1024).toFixed(1)} KB
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Link href={`/resumes/${resume.resume_id}`}>
                      <Button variant="outline" size="sm" className="gap-1">
                        <Eye className="h-3 w-3" />
                        查看
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => handleDownload(resume.resume_id)}
                    >
                      <Download className="h-3 w-3" />
                      PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
