import type { TemplateMeta } from "./shared";

/** 所有可用模板的元信息（用于模板选择 UI） */
export const TEMPLATE_LIST: TemplateMeta[] = [
  {
    name: "professional",
    label: "商务",
    description: "双栏侧边栏布局，深色侧栏配亮色主区域，适合互联网/科技行业",
    color: "#3b82f6",
    category: "professional",
  },
  {
    name: "academic",
    label: "学术",
    description: "单栏居中布局，经典学术风格，适合教育/研究/金融行业",
    color: "#1a1a2e",
    category: "professional",
  },
  {
    name: "creative",
    label: "创意",
    description: "渐变色头部配卡片式内容，视觉冲击力强，适合设计/营销行业",
    color: "#7c3aed",
    category: "creative",
  },
  {
    name: "minimal",
    label: "极简",
    description: "大量留白，纯黑白配色，仅用字号区分层级，适合外企/互联网",
    color: "#18181b",
    category: "minimal",
  },
  {
    name: "elegant",
    label: "优雅",
    description: "深蓝金色系，经典排版，适合高端岗位/金融/咨询行业",
    color: "#b8860b",
    category: "professional",
  },
  {
    name: "tech",
    label: "科技",
    description: "深色侧栏+亮色内容区，代码风格标签，适合程序员/工程师",
    color: "#10b981",
    category: "creative",
  },
  {
    name: "compact",
    label: "紧凑",
    description: "信息密度高，减少留白，适合经历丰富的资深岗位",
    color: "#64748b",
    category: "minimal",
  },
];
