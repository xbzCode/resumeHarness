"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Brain, FileText, Edit3, Save, X, Upload } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi, type MemoryDoc, API_BASE } from "@/lib/api";
import { toast } from "sonner";

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
        // 简历原文需要通过 upload 接口更新
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

    // 清空 input，允许重复上传同文件
    e.target.value = "";
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <h2 className="text-sm font-medium">记忆管理</h2>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{memories.length} 个文件</Badge>
          <label>
            <input
              id="resume-upload"
              type="file"
              accept=".md,.txt,.pdf"
              className="hidden"
              onChange={handleUploadResume}
            />
            <Button variant="outline" size="sm" className="gap-1" onClick={() => document.getElementById("resume-upload")?.click()}>
              <Upload className="h-3 w-3" />
              上传简历
            </Button>
          </label>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="list" className="flex h-full flex-col">
          <TabsList className="mx-4 mt-2 w-fit">
            <TabsTrigger value="list">文件列表</TabsTrigger>
            <TabsTrigger value="content" disabled={!selected}>
              内容详情
            </TabsTrigger>
          </TabsList>

          <TabsContent value="list" className="flex-1 overflow-auto p-4">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16" />
                ))}
              </div>
            ) : memories.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                  <Brain className="h-8 w-8 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold">暂无记忆</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    上传简历或在对话中让 AI 写入记忆
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {memories.map((mem) => (
                  <Card
                    key={mem.name}
                    className={`cursor-pointer transition-colors hover:bg-accent ${
                      selected === mem.name ? "ring-2 ring-primary" : ""
                    }`}
                    onClick={() => selectMemory(mem.name)}
                  >
                    <CardContent className="flex items-center gap-3 p-3">
                      <FileText className="h-5 w-5 text-primary shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{mem.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(mem.size_bytes / 1024).toFixed(1)} KB · {new Date(mem.modified_at * 1000).toLocaleString("zh-CN")}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="content" className="flex-1 overflow-hidden">
            {selected && (
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b px-4 py-2">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    <span className="text-sm font-medium">{selected}</span>
                  </div>
                  <div className="flex gap-2">
                    {editing ? (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleCancelEdit}
                        >
                          <X className="mr-1 h-3 w-3" />
                          取消
                        </Button>
                        <Button size="sm" onClick={handleSave}>
                          <Save className="mr-1 h-3 w-3" />
                          保存
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditing(true)}
                      >
                        <Edit3 className="mr-1 h-3 w-3" />
                        编辑
                      </Button>
                    )}
                  </div>
                </div>
                <div className="flex-1 overflow-auto p-4">
                  {editing ? (
                    <Textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="min-h-[400px] font-mono text-sm"
                    />
                  ) : (
                    <article className="prose prose-slate max-w-none dark:prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {content}
                      </ReactMarkdown>
                    </article>
                  )}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
