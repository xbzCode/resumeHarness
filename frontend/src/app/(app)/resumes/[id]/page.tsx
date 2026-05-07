"use client";

import { useEffect, useState, useCallback } from "react";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ArrowLeft,
  Download,
  Trash2,
  FileText,
  Eye,
  Code,
  Loader2,
  Pencil,
  Check,
  X,
  FileDown,
  Share2,
  Copy,
  RefreshCw,
  ChevronDown,
  Globe,
  FileSpreadsheet,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, downloadFile, fetchText, fetchJson } from "@/lib/api";
import { copyToClipboard } from "@/lib/clipboard";
import { TEMPLATE_LIST } from "@/components/templates/registry";
import { ResumePreview } from "@/components/resume-preview";
import type { ResumeData } from "@/store/chat";
import { toast } from "sonner";

/** 后端 /api/resume/{id}/data 返回的结构 */
interface ResumeDataResponse {
  resume_id: string;
  data: ResumeData;
  available_templates: string[];
}

/** 后端 /api/resume/{id}/share 返回的结构 */
interface ShareLinkResponse {
  share_id: string | null;
  share_url: string | null;
  created_at?: number;
}

/** 清除编辑数据中的空条目 */
function cleanEmptyItems(data: ResumeData): ResumeData {
  const d = JSON.parse(JSON.stringify(data)) as ResumeData;
  d.experience = d.experience.filter(
    (exp) => exp.title || exp.company || exp.period || exp.highlights.some((h) => h)
  );
  d.education = d.education.filter(
    (edu) => edu.school || edu.degree || edu.major || edu.period || edu.achievements.some((a) => a)
  );
  d.skills = d.skills.filter(
    (cat) => cat.category || cat.skills.some((s) => s)
  );
  d.projects = d.projects.filter(
    (proj) => proj.name || proj.role || proj.period || proj.description || proj.contributions.some((c) => c)
  );
  // 清除子列表中的空项
  d.experience.forEach((exp) => {
    exp.highlights = exp.highlights.filter((h) => h);
  });
  d.education.forEach((edu) => {
    edu.achievements = edu.achievements.filter((a) => a);
  });
  d.projects.forEach((proj) => {
    proj.contributions = proj.contributions.filter((c) => c);
  });
  return d;
}

export default function ResumeDetailPage() {
  const router = useRouter();
  const params = useParams();
  const resumeId = params.id as string;
  const { token } = useAuthStore();
  const [resumeData, setResumeData] = useState<ResumeData | null>(null);
  const [editData, setEditData] = useState<ResumeData | null>(null);
  const [markdownContent, setMarkdownContent] = useState<string | null>(null);
  const [markdownLoading, setMarkdownLoading] = useState(false);
  const [activeTemplate, setActiveTemplate] = useState("professional");
  const [loading, setLoading] = useState(true);
  const [showDelete, setShowDelete] = useState(false);
  const [viewMode, setViewMode] = useState<"preview" | "markdown">("preview");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // 下载状态
  const [downloading, setDownloading] = useState<string | null>(null); // "pdf" | "docx" | null

  // 分享状态
  const [showShare, setShowShare] = useState(false);
  const [shareInfo, setShareInfo] = useState<ShareLinkResponse | null>(null);
  const [shareLoading, setShareLoading] = useState(false);

  useEffect(() => {
    loadResume();
  }, [resumeId]);

  async function loadResume() {
    if (!token) return;
    try {
      const dataRes = await fetchJson<ResumeDataResponse>(token, `/api/resume/${resumeId}/data`);
      setResumeData(dataRes.data);
      setActiveTemplate(dataRes.available_templates?.[0] || "professional");
    } catch {
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
    if (editing) return;
    setViewMode("markdown");
    if (markdownContent !== null) return;
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

  /** 进入编辑模式 */
  function handleStartEdit() {
    if (!resumeData) return;
    setEditData(JSON.parse(JSON.stringify(resumeData)));
    setEditing(true);
  }

  /** 取消编辑 */
  function handleCancelEdit() {
    setEditData(null);
    setEditing(false);
  }

  /** 保存编辑（自动清除空条目） */
  async function handleSaveEdit() {
    if (!token || !editData) return;
    setSaving(true);
    try {
      // 清除空条目
      const cleaned = cleanEmptyItems(editData);
      const result = await createAuthApi(token)(`/api/resume/${resumeId}/data`, {
        method: "PUT",
        body: cleaned,
      });
      setResumeData((result as { data: ResumeData }).data);
      setEditData(null);
      setEditing(false);
      setMarkdownContent(null);
      toast.success("保存成功");
    } catch {
      toast.error("保存失败");
    } finally {
      setSaving(false);
    }
  }

  /** 编辑模式下的数据变更 */
  const handleDataChange = useCallback((newData: ResumeData) => {
    setEditData(newData);
  }, []);

  // ----- 下载功能 -----

  /** 后端下载 PDF */
  async function handleDownloadPdf() {
    if (!token) return;
    setDownloading("pdf");
    try {
      const blob = await downloadFile(token, `/api/resume/${resumeId}/download?format=pdf&template=${activeTemplate}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${resumeId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("PDF 下载失败");
    } finally {
      setDownloading(null);
    }
  }

  /** 后端下载 DOCX */
  async function handleDownloadDocx() {
    if (!token) return;
    setDownloading("docx");
    try {
      const blob = await downloadFile(token, `/api/resume/${resumeId}/download?format=docx&template=${activeTemplate}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${resumeId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("DOCX 下载失败");
    } finally {
      setDownloading(null);
    }
  }

  /** 下载 HTML */
  async function handleDownloadHtml() {
    if (!token) return;
    setDownloading("html");
    try {
      const blob = await downloadFile(token, `/api/resume/${resumeId}/download?format=html&template=${activeTemplate}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${resumeId}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("HTML 下载失败");
    } finally {
      setDownloading(null);
    }
  }

  /** 下载 Markdown */
  async function handleDownloadMd() {
    if (!token) return;
    setDownloading("md");
    try {
      let content = markdownContent;
      if (!content) {
        content = await fetchText(token, `/api/resume/${resumeId}/download?format=markdown`);
      }
      const blob = new Blob([content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${resumeId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Markdown 下载失败");
    } finally {
      setDownloading(null);
    }
  }

  // ----- 分享功能 -----

  /** 打开分享对话框，加载分享信息 */
  async function handleOpenShare() {
    if (!token) return;
    setShowShare(true);
    if (!shareInfo) {
      setShareLoading(true);
      try {
        const data = await createAuthApi(token)(`/api/resume/${resumeId}/share`);
        setShareInfo(data as ShareLinkResponse);
      } catch {
        setShareInfo(null);
      } finally {
        setShareLoading(false);
      }
    }
  }

  /** 生成/重新生成分享链接 */
  async function handleCreateShareLink() {
    if (!token) return;
    setShareLoading(true);
    try {
      const data = await createAuthApi(token)(`/api/resume/${resumeId}/share`, { method: "POST" });
      setShareInfo(data as ShareLinkResponse);
      toast.success("分享链接已生成");
    } catch {
      toast.error("生成分享链接失败");
    } finally {
      setShareLoading(false);
    }
  }

  /** 复制分享链接 */
  async function handleCopyShareLink() {
    if (!shareInfo?.share_url) return;
    const baseUrl = window.location.origin;
    const fullUrl = `${baseUrl}${shareInfo.share_url}`;
    const ok = await copyToClipboard(fullUrl);
    if (ok) {
      toast.success("链接已复制到剪贴板");
    } else {
      toast.error("复制失败");
    }
  }

  /** 撤销分享链接 */
  async function handleDeleteShareLink() {
    if (!token) return;
    try {
      await createAuthApi(token)(`/api/resume/${resumeId}/share`, { method: "DELETE" });
      setShareInfo(null);
      toast.success("分享链接已撤销");
    } catch {
      toast.error("撤销失败");
    }
  }

  async function handleDelete() {
    if (!token) return;
    try {
      await createAuthApi(token)(`/api/resume/${resumeId}`, { method: "DELETE" });
      toast.success("已删除");
      router.push("/resumes");
    } catch {
      toast.error("删除失败");
    }
  }

  const isDownloading = downloading !== null;

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">简历 {resumeId.slice(0, 12)}</span>
          {editing && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">编辑中</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            /* 编辑模式按钮组 */
            <>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={handleCancelEdit}
                disabled={saving}
              >
                <X className="h-3 w-3" />
                取消
              </Button>
              <Button
                size="sm"
                className="gap-1"
                onClick={handleSaveEdit}
                disabled={saving}
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                {saving ? "保存中…" : "完成"}
              </Button>
            </>
          ) : (
            /* 非编辑模式按钮组 */
            <>
              {/* 编辑按钮 */}
              {resumeData && viewMode === "preview" && (
                <>
                  <Button variant="outline" size="sm" className="gap-1" onClick={handleStartEdit}>
                    <Pencil className="h-3 w-3" />
                    编辑
                  </Button>
                  <Separator orientation="vertical" className="h-6" />
                </>
              )}
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
                <DropdownMenu>
                  <DropdownMenuTrigger render={<Button variant="outline" size="sm" className="gap-1" />}>
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TEMPLATE_LIST.find(t => t.name === activeTemplate)?.color || "#3b82f6" }} />
                    {TEMPLATE_LIST.find(t => t.name === activeTemplate)?.label || "模板"}
                    <ChevronDown className="h-3 w-3 ml-0.5" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    {TEMPLATE_LIST.map((tpl) => (
                      <DropdownMenuItem
                        key={tpl.name}
                        onClick={() => setActiveTemplate(tpl.name)}
                        className={activeTemplate === tpl.name ? "bg-accent" : ""}
                      >
                        <div className="flex items-center gap-2 w-full">
                          <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: tpl.color }} />
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
              )}
              <Separator orientation="vertical" className="h-6" />
              {/* 分享按钮 */}
              <Button variant="outline" size="sm" className="gap-1" onClick={handleOpenShare}>
                <Share2 className="h-3 w-3" />
                分享
              </Button>
              {/* 下载下拉菜单 */}
              <DropdownMenu>
                <DropdownMenuTrigger render={<Button size="sm" className="gap-1" disabled={isDownloading} />}>
                  {isDownloading ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Download className="h-3 w-3" />
                  )}
                  下载
                  <ChevronDown className="h-3 w-3 ml-0.5" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleDownloadPdf} disabled={downloading === "pdf"}>
                    <FileDown className="h-4 w-4 mr-2" />
                    PDF
                    {downloading === "pdf" && <Loader2 className="h-3 w-3 animate-spin ml-auto" />}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleDownloadDocx} disabled={downloading === "docx"}>
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Word (DOCX)
                    {downloading === "docx" && <Loader2 className="h-3 w-3 animate-spin ml-auto" />}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleDownloadHtml} disabled={downloading === "html"}>
                    <Globe className="h-4 w-4 mr-2" />
                    HTML
                    {downloading === "html" && <Loader2 className="h-3 w-3 animate-spin ml-auto" />}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleDownloadMd} disabled={downloading === "md"}>
                    <FileText className="h-4 w-4 mr-2" />
                    Markdown
                    {downloading === "md" && <Loader2 className="h-3 w-3 animate-spin ml-auto" />}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              {/* 删除 */}
              <Dialog open={showDelete} onOpenChange={setShowDelete}>
                <DialogTrigger render={<Button variant="ghost" size="icon" className="text-destructive" />}>
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
            </>
          )}
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
        ) : viewMode === "preview" && (resumeData || editData) ? (
          <div className="mx-auto flex justify-center">
            <div className="w-[210mm] min-h-[297mm] bg-white shadow-lg">
              <ResumePreview
                data={editing && editData ? editData : resumeData!}
                template={activeTemplate}
                editable={editing}
                onChange={editing ? handleDataChange : undefined}
              />
            </div>
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

      {/* 分享对话框 */}
      <Dialog open={showShare} onOpenChange={setShowShare}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>分享简历</DialogTitle>
            <DialogDescription>
              生成一个公开链接，任何人无需登录即可查看你的简历。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {shareLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">加载中…</span>
              </div>
            ) : shareInfo?.share_url ? (
              <div className="space-y-4">
                {/* 当前链接 */}
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-md border bg-muted px-3 py-2 text-sm font-mono break-all">
                    {typeof window !== "undefined"
                      ? `${window.location.origin}${shareInfo.share_url}`
                      : shareInfo.share_url}
                  </div>
                  <Button variant="outline" size="icon" onClick={handleCopyShareLink} title="复制链接">
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  任何拥有此链接的人都可以查看简历（HTML 格式）。
                  在链接后添加 <code className="bg-muted px-1 rounded">?format=pdf</code> 可直接下载 PDF。
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={handleCreateShareLink}
                    disabled={shareLoading}
                  >
                    <RefreshCw className="h-3 w-3" />
                    重新生成
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1 text-destructive hover:text-destructive"
                    onClick={handleDeleteShareLink}
                  >
                    <X className="h-3 w-3" />
                    撤销链接
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-4">
                <Globe className="h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">尚未生成分享链接</p>
                <Button onClick={handleCreateShareLink} disabled={shareLoading} className="gap-1">
                  <Share2 className="h-4 w-4" />
                  生成分享链接
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
