"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Info,
  Bot,
  Sparkles,
  FileText,
  Brain,
  Wrench,
  Shield,
  Zap,
  Star,
  BookOpen,
  Server,
  Layout,
  Heart,
} from "lucide-react";

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// 功能特性数据
// ---------------------------------------------------------------------------

const FEATURES = [
  {
    icon: Bot,
    title: "AI 驱动",
    description: "基于大语言模型的智能简历优化，精准匹配岗位需求，支持多轮迭代优化",
  },
  {
    icon: FileText,
    title: "多模板渲染",
    description: "7 套精美模板（商务/学术/创意/极简/优雅/科技/紧凑），支持在线预览、原地编辑、拖拽排序",
  },
  {
    icon: Brain,
    title: "记忆系统",
    description: "自动学习用户偏好与职业信息，越用越懂你，支持自定义指令注入",
  },
  {
    icon: Sparkles,
    title: "行业感知",
    description: "互联网/金融等行业专项技能自动匹配，JD 解析与关键词分析，智能推荐模板",
  },
  {
    icon: Wrench,
    title: "MCP 工具",
    description: "邮件发送、PDF 转换、JD 抓取等可扩展工具链，支持用户级认证配置",
  },
  {
    icon: Shield,
    title: "多租户隔离",
    description: "每用户独立数据空间，JWT 认证保障安全，简历与记忆完全私密",
  },
  {
    icon: Zap,
    title: "实时流式",
    description: "SSE 流式对话，实时查看生成进度、思考过程与工具调用",
  },
  {
    icon: Star,
    title: "简历评分",
    description: "5 维度加权评分（结构/内容/量化/关键词/格式），自动检测薄弱环节并给出建议",
  },
];

// ---------------------------------------------------------------------------
// 技术栈数据
// ---------------------------------------------------------------------------

const TECH_STACK = [
  { category: "Agent 框架", items: ["OpenHarness (裁剪复用)", "QueryEngine", "Tool Registry"] },
  { category: "LLM", items: ["DeepSeek API", "多 Key 轮询", "OpenAI 兼容协议"] },
  { category: "后端", items: ["FastAPI", "uvicorn", "SQLite", "Jinja2"] },
  { category: "前端", items: ["Next.js 16", "React 19", "Tailwind CSS v4", "shadcn/ui"] },
  { category: "PDF", items: ["weasyprint", "xhtml2pdf", "fpdf2"] },
  { category: "MCP", items: ["HTTP MCP 协议", "McpServerBase", "工具 Annotations"] },
];

// ---------------------------------------------------------------------------
// 项目里程碑
// ---------------------------------------------------------------------------

const MILESTONES = [
  { phase: "P0", name: "Agent 核心可用版", status: "completed" },
  { phase: "P1", name: "Web 服务可用版", status: "completed" },
  { phase: "P2", name: "多用户版", status: "completed" },
  { phase: "P3", name: "质量增强版", status: "completed" },
  { phase: "P4", name: "体验优化版", status: "completed" },
  { phase: "P5", name: "IM 渠道版", status: "planned" },
];

// ---------------------------------------------------------------------------
// 主页面
// ---------------------------------------------------------------------------

export default function AboutPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center border-b px-4">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-medium">关于</h2>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* 项目介绍 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                  <Bot className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-lg">Resume Agent</CardTitle>
                  <CardDescription>智能简历优化助手</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Resume Agent 是一个基于 AI 的智能简历优化工具。它结合用户简历与招聘岗位 JD，
                通过大语言模型智能生成匹配岗位的优化简历。支持 7 套模板在线预览与原地编辑、
                5 维度简历评分、行业感知与 JD 解析、记忆系统与 MCP 工具链等核心能力，
                让简历优化变得高效而专业。
              </p>
              <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
                <Badge variant="secondary">v0.4.0</Badge>
                <span>基于 OpenHarness 重构</span>
              </div>
            </CardContent>
          </Card>

          {/* 功能特性 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">核心特性</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                {FEATURES.map((feature) => {
                  const Icon = feature.icon;
                  return (
                    <div
                      key={feature.title}
                      className="flex items-start gap-3 rounded-lg border p-3"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{feature.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {feature.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* 技术栈 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Wrench className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">技术栈</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                {TECH_STACK.map((group) => (
                  <div key={group.category}>
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      {group.category}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {group.items.map((item) => (
                        <Badge key={item} variant="secondary" className="text-xs">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 开发里程碑 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">开发里程碑</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {MILESTONES.map((milestone) => (
                  <div
                    key={milestone.phase}
                    className="flex items-center gap-3"
                  >
                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                        milestone.status === "completed"
                          ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {milestone.phase.replace("P", "")}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{milestone.name}</p>
                    </div>
                    <Badge
                      variant={
                        milestone.status === "completed" ? "default" : "outline"
                      }
                      className="text-[10px]"
                    >
                      {milestone.status === "completed" ? "已完成" : "规划中"}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 系统架构入口 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Layout className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">系统模块</CardTitle>
              </div>
              <CardDescription>Resume Agent 的核心模块与能力</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  { icon: Bot, label: "Agent 核心", desc: "QueryEngine + RuntimeBundle", href: "/chat" },
                  { icon: FileText, label: "简历渲染", desc: "ResumeData + Jinja2 + PDF", href: "/resumes" },
                  { icon: Brain, label: "记忆系统", desc: "用户偏好 + 越用越好", href: "/memory" },
                  { icon: BookOpen, label: "技能系统", desc: "Front Matter + 行业映射", href: "/skills" },
                  { icon: Server, label: "MCP 服务", desc: "HTTP 工具链 + 认证", href: "/mcp" },
                  { icon: Layout, label: "模板系统", desc: "注册表 + 元数据规范", href: "/templates" },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.label}
                      href={item.href}
                      className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-accent"
                    >
                      <Icon className="h-5 w-5 text-primary shrink-0" />
                      <div>
                        <p className="text-sm font-medium">{item.label}</p>
                        <p className="text-xs text-muted-foreground">{item.desc}</p>
                      </div>
                    </a>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* 项目链接 */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <GitHubIcon className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">开源项目</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <a
                  href="https://github.com/xbzCode/resumeHarness"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors hover:bg-accent"
                >
                  <GitHubIcon className="h-4 w-4" />
                  <span>GitHub 仓库</span>
                </a>
                <span className="text-xs text-muted-foreground">
                  欢迎 Star、Issue 和 PR
                </span>
              </div>
            </CardContent>
          </Card>

          {/* 致谢 */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Heart className="h-4 w-4 text-red-500" />
                <span>基于 OpenHarness 构建</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
