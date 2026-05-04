"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  BookOpen,
  Tag,
  Building2,
  Link2,
  Coins,
  User,
  FileText,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { createAuthApi } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

interface SkillMeta {
  name: string;
  found: boolean;
  size_bytes?: number;
  modified_at?: number;
  preview?: string;
  version?: string;
  category?: string;
  tags?: string[];
  industry?: string[];
  depends?: string[];
  token_budget?: number;
  author?: string;
  description?: string;
}

// ---------------------------------------------------------------------------
// 分类颜色映射
// ---------------------------------------------------------------------------

const CATEGORY_COLORS: Record<string, string> = {
  通用技能: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  行业技能: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  JD解析: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
};

function getCategoryColor(category?: string): string {
  if (!category) return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  for (const [key, color] of Object.entries(CATEGORY_COLORS)) {
    if (category.includes(key)) return color;
  }
  return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
}

// ---------------------------------------------------------------------------
// Skill 列表视图
// ---------------------------------------------------------------------------

function SkillListView({
  skills,
  onSelect,
}: {
  skills: SkillMeta[];
  onSelect: (name: string) => void;
}) {
  // 按分类分组
  const grouped = skills.reduce<Record<string, SkillMeta[]>>((acc, skill) => {
    const cat = skill.category || "其他";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(skill);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <div className="mb-3 flex items-center gap-2">
            <Badge className={cn("text-xs", getCategoryColor(category))}>
              {category}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {items.length} 个技能
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {items.map((skill) => (
              <Card
                key={skill.name}
                className="cursor-pointer transition-all hover:shadow-md hover:border-primary/30"
                onClick={() => onSelect(skill.name)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm font-medium">
                      {skill.name}
                    </CardTitle>
                    {skill.version && (
                      <Badge variant="outline" className="text-[10px] shrink-0">
                        v{skill.version}
                      </Badge>
                    )}
                  </div>
                  {skill.description && (
                    <CardDescription className="text-xs line-clamp-2">
                      {skill.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-1">
                    {skill.tags?.slice(0, 4).map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="text-[10px] px-1.5 py-0"
                      >
                        {tag}
                      </Badge>
                    ))}
                    {(skill.tags?.length ?? 0) > 4 && (
                      <Badge
                        variant="secondary"
                        className="text-[10px] px-1.5 py-0"
                      >
                        +{skill.tags!.length - 4}
                      </Badge>
                    )}
                  </div>
                  {skill.industry && skill.industry.length > 0 && (
                    <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Building2 className="h-3 w-3" />
                      {skill.industry.join(", ")}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skill 详情视图
// ---------------------------------------------------------------------------

function SkillDetailView({
  skill,
  content,
  loadingContent,
  onBack,
}: {
  skill: SkillMeta;
  content: string | null;
  loadingContent: boolean;
  onBack: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* 返回按钮 */}
      <Button variant="ghost" size="sm" onClick={onBack} className="gap-1">
        <ArrowLeft className="h-4 w-4" />
        返回列表
      </Button>

      {/* 元数据卡片 */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div>
              <CardTitle className="text-base">{skill.name}</CardTitle>
              {skill.description && (
                <CardDescription className="mt-1">
                  {skill.description}
                </CardDescription>
              )}
            </div>
            <Badge className={cn("text-xs", getCategoryColor(skill.category))}>
              {skill.category || "其他"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {/* 基本信息 */}
            {skill.version && (
              <div className="flex items-center gap-2 text-sm">
                <Tag className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">版本</span>
                <span className="font-medium">{skill.version}</span>
              </div>
            )}
            {skill.author && (
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">作者</span>
                <span className="font-medium">{skill.author}</span>
              </div>
            )}
            {skill.token_budget && (
              <div className="flex items-center gap-2 text-sm">
                <Coins className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Token 预算</span>
                <span className="font-medium">{skill.token_budget}</span>
              </div>
            )}
            {skill.size_bytes && (
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">文件大小</span>
                <span className="font-medium">
                  {(skill.size_bytes / 1024).toFixed(1)} KB
                </span>
              </div>
            )}
          </div>

          {/* 标签 */}
          {skill.tags && skill.tags.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1 text-xs text-muted-foreground">
                <Tag className="h-3 w-3" />
                标签
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skill.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* 适用行业 */}
          {skill.industry && skill.industry.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1 text-xs text-muted-foreground">
                <Building2 className="h-3 w-3" />
                适用行业
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skill.industry.map((ind) => (
                  <Badge key={ind} variant="outline" className="text-xs">
                    {ind}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* 依赖 */}
          {skill.depends && skill.depends.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1 text-xs text-muted-foreground">
                <Link2 className="h-3 w-3" />
                依赖技能
              </div>
              <div className="flex flex-wrap gap-1.5">
                {skill.depends.map((dep) => (
                  <Badge key={dep} variant="outline" className="text-xs">
                    {dep}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 内容预览 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">技能内容</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingContent ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : content ? (
            <article className="prose prose-slate max-w-none dark:prose-invert prose-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </article>
          ) : (
            <p className="text-sm text-muted-foreground">无法加载技能内容</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 主页面
// ---------------------------------------------------------------------------

export default function SkillsPage() {
  const { token } = useAuthStore();
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [skillDetail, setSkillDetail] = useState<SkillMeta | null>(null);
  const [skillContent, setSkillContent] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);

  useEffect(() => {
    loadSkills();
  }, []);

  async function loadSkills() {
    if (!token) return;
    setLoading(true);
    try {
      const api = createAuthApi(token);
      const data = await api<{ skills: SkillMeta[] }>("/api/skills");
      setSkills(data.skills || []);
    } catch {
      toast.error("加载技能列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function selectSkill(name: string) {
    if (!token) return;
    setSelectedSkill(name);
    setSkillContent(null);
    setLoadingContent(true);

    // 从列表中找到已有的元数据
    const existing = skills.find((s) => s.name === name);
    if (existing) {
      setSkillDetail(existing);
    }

    try {
      const api = createAuthApi(token);
      // 并行加载详情和内容
      const [detailData, contentData] = await Promise.all([
        api<SkillMeta>(`/api/skills/${name}`).catch(() => existing),
        api<{ name: string; content: string }>(`/api/skills/${name}/content`).catch(() => null),
      ]);
      setSkillDetail(detailData);
      if (contentData) {
        setSkillContent(contentData.content);
      }
    } catch {
      toast.error("加载技能详情失败");
    } finally {
      setLoadingContent(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-medium">技能管理</h2>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{skills.length} 个技能</Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={loadSkills}
            disabled={loading}
            className="gap-1"
          >
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
            刷新
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-3xl">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-28" />
              ))}
            </div>
          ) : selectedSkill && skillDetail ? (
            <SkillDetailView
              skill={skillDetail}
              content={skillContent}
              loadingContent={loadingContent}
              onBack={() => {
                setSelectedSkill(null);
                setSkillDetail(null);
                setSkillContent(null);
              }}
            />
          ) : skills.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <BookOpen className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold">暂无技能</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  系统中暂无已注册的技能文件
                </p>
              </div>
            </div>
          ) : (
            <SkillListView skills={skills} onSelect={selectSkill} />
          )}
        </div>
      </div>
    </div>
  );
}
