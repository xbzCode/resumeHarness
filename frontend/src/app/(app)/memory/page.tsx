"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Brain, FileText, Edit3, Save, X, Upload, Plus } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, type MemoryDoc, API_BASE } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function MemoryPage() {
  const { token } = useAuthStore();
  const [memories, setMemories] = useState<MemoryDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");

  useEffect(() => {
    loadMemories();
  }, []);

  async function loadMemories() {
    if (!token) return;
    try {
      const api = createAuthApi(token);
      const data = await api<{ documents: MemoryDoc[] }>("/api/memory");
      const docs = data.documents || [];
      setMemories(docs);
      if (docs.length > 0 && !selected) {
        selectMemory(docs[0].name);
      }
    } catch {
      toast.error("加载记忆列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function selectMemory(name: string) {
    if (!token) return;
    setSelected(name);
    setEditing(false);
    try {
      const api = createAuthApi(token);
      const data = await api<{ name: string; content: string }>(
        `/api/memory/${encodeURIComponent(name)}`,
      );
      setContent(data.content);
      setEditContent(data.content);
    } catch {
      toast.error("加载记忆内容失败");
    }
  }

  async function handleSave() {
    if (!token || !selected) return;
    try {
      if (selected === "简历原文.md") {
        const blob = new Blob([editContent], { type: "text/markdown" });
        const file = new File([blob], "简历原文.md", { type: "text/markdown" });
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API_BASE}/api/memory/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `保存失败: HTTP ${res.status}`);
        }
      } else {
        const api = createAuthApi(token);
        await api(`/api/memory/${encodeURIComponent(selected)}`, {
          method: "PUT",
          body: { content: editContent, mode: "replace" },
        });
      }
      setContent(editContent);
      setEditing(false);
      toast.success("保存成功");
      loadMemories();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "保存失败");
    }
  }

  function handleCancelEdit() {
    setEditing(false);
    setEditContent(content);
  }

  async function handleUploadResume(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/memory/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `上传失败: HTTP ${res.status}`);
      }
      toast.success("简历已上传");
      loadMemories();
      selectMemory("简历原文.md");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "上传失败");
    }

    e.target.value = "";
  }

  const selectedMemory = memories.find((m) => m.name === selected);

  return (
    <div className="flex h-full">
      {/* 左栏 - 文件列表 */}
      <div className="w-64 shrink-0 border-r flex flex-col">
        {/* 顶栏 */}
        <div className="flex h-12 items-center justify-between border-b px-4">
          <h2 className="text-sm font-medium">记忆管理</h2>
          <label>
            <input
              id="resume-upload"
              type="file"
              accept=".md,.txt,.pdf"
              className="hidden"
              onChange={handleUploadResume}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => document.getElementById("resume-upload")?.click()}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </label>
        </div>

        {/* 文件列表 */}
        <ScrollArea className="flex-1">
          {loading ? (
            <div className="space-y-2 p-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14" />
              ))}
            </div>
          ) : memories.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 px-4 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted">
                <Brain className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-xs text-muted-foreground">
                上传简历或对话生成
              </p>
            </div>
          ) : (
            <div className="p-2 space-y-0.5">
              {memories.map((mem) => (
                <button
                  key={mem.name}
                  type="button"
                  onClick={() => selectMemory(mem.name)}
                  className={cn(
                    "flex w-full items-start gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors",
                    selected === mem.name
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                  )}
                >
                  <FileText className="h-4 w-4 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm truncate font-medium leading-tight">{mem.name}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      {(mem.size_bytes / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* 上传按钮 */}
        <div className="border-t p-3">
          <label className="block">
            <input
              type="file"
              accept=".md,.txt,.pdf"
              className="hidden"
              onChange={handleUploadResume}
            />
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-1.5"
              onClick={() => document.getElementById("resume-upload")?.click()}
            >
              <Upload className="h-3.5 w-3.5" />
              上传简历
            </Button>
          </label>
        </div>
      </div>

      {/* 右栏 - 文件内容 */}
      <div className="flex-1 flex flex-col min-w-0">
        {selected ? (
          <>
            {/* 内容顶栏 */}
            <div className="flex h-12 items-center justify-between border-b px-6">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="text-sm font-medium truncate">{selected}</span>
                {selectedMemory && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {new Date(selectedMemory.modified_at * 1000).toLocaleString("zh-CN")}
                  </span>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0">
                {editing ? (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCancelEdit}
                      className="gap-1"
                    >
                      <X className="h-3.5 w-3.5" />
                      取消
                    </Button>
                    <Button size="sm" onClick={handleSave} className="gap-1">
                      <Save className="h-3.5 w-3.5" />
                      保存
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEditing(true)}
                    className="gap-1"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    编辑
                  </Button>
                )}
              </div>
            </div>

            {/* 内容区 */}
            {editing ? (
              <div className="flex-1 p-4 min-h-0">
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="h-full font-mono text-sm leading-relaxed resize-none"
                />
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto min-h-0">
                <div className="p-6">
                  <article className="prose prose-slate max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {content}
                    </ReactMarkdown>
                  </article>
                </div>
              </div>
            )}
          </>
        ) : (
          /* 未选中文件 */
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
              <Brain className="h-7 w-7 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium">选择一个文件</p>
              <p className="mt-1 text-xs text-muted-foreground">
                从左侧列表选择文件查看内容
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
