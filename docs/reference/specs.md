# 扩展规范设计

> **文档来源**：从 `后续优化.md` 第二章提取，保留项目技术规范的权威参考。
>
> **文档状态**：大部分规范已落地实现，本文档作为规范基准持续维护。

---

## 核心原则

每个可扩展点必须定义 **格式规范 + 元数据规范 + 验证规则 + 集成指南**，第三方按规范即可接入，无需改代码。

---

## 2.1 Skill 规范

### 2.1.1 格式规范

Skill 文件为 **Markdown + YAML Front Matter** 格式：

```markdown
---
name: resume-tech
version: "1.0.0"
category: 行业技能
tags: [互联网, 科技, 前端, 后端, AI]
industry: [tech, internet]
depends: [resume-skill]
token_budget: 4000
author: ResumeAgent
description: 互联网/科技行业专项技能
---

## 行业概述
（技能正文内容...）
```

### 2.1.2 Front Matter 元数据规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 技能唯一标识符，与文件名 stem 一致 |
| `version` | string | 是 | 语义化版本号（SemVer） |
| `category` | string | 是 | 分类标签，用于 UI 展示分组 |
| `tags` | string[] | 否 | 关键词标签，用于搜索和推荐 |
| `industry` | string[] | 否 | 适用行业标识符列表 |
| `depends` | string[] | 否 | 依赖的其他技能名称列表 |
| `token_budget` | int | 否 | 预估 Token 占用 |
| `author` | string | 否 | 作者/来源 |
| `description` | string | 是 | 技能描述（一句话） |

### 2.1.3 验证规则

- Front Matter 必须存在且包含 `name`、`version`、`category`、`description`
- `name` 必须与文件名 stem 一致，格式：`^[a-z][a-z0-9-]*$`
- `depends` 中引用的技能必须存在
- 文件大小不超过 64KB
- 正文必须包含至少一个 `##` 级标题

---

## 2.2 MCP 服务器规范

### 2.2.1 协议规范

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/tools/list` | POST | 工具发现 |
| `/tools/call` | POST | 工具调用 |

### 2.2.2 ToolSpec Annotations 规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `readOnlyHint` | bool | 是 | 是否只读 |
| `destructiveHint` | bool | 是 | 是否有破坏性 |
| `idempotentHint` | bool | 否 | 是否幂等 |
| `category` | string | 否 | 工具分类标签 |
| `timeout_ms` | int | 否 | 建议超时时间（毫秒） |

> `is_read_only()` 不再通过名称魔法推断，改为读取 `annotations.readOnlyHint`。

### 2.2.3 MCP 服务器注册配置规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 传输协议，当前仅 `"http"` |
| `url` | string | 是 | 服务器地址 |
| `headers` | object | 否 | 全局请求头 |
| `enabled` | bool | 否 | 是否启用 |
| `description` | string | 否 | 服务器描述 |
| `auto_reconnect` | bool | 否 | 自动重连 |
| `health_check_interval` | int | 否 | 健康检查间隔（秒） |

### 2.2.4 共享 MCP 框架

提供 `McpServerBase` 基类，子类只需 `register_tool + handler`。

---

## 2.3 简历模板规范

### 2.3.1 文件结构

```
templates/{template_name}/
├── template.json      # 模板元数据（必填）
├── template.html      # Jinja2 HTML 模板（必填）
├── preview.png        # 预览缩略图（推荐）
└── README.md          # 模板说明（推荐）
```

### 2.3.2 template.json 元数据规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 模板唯一标识符，与目录名一致 |
| `version` | string | 是 | 语义化版本号 |
| `display_name` | string | 是 | UI 展示名称 |
| `description` | string | 是 | 模板风格描述 |
| `layout` | string | 否 | 布局类型 |
| `color_scheme` | object | 否 | 主色方案 |
| `recommended_industries` | string[] | 否 | 推荐行业 |
| `supports_dark_mode` | bool | 否 | 是否支持暗色主题 |
| `page_size` | string | 否 | 页面尺寸，默认 A4 |

### 2.3.3 验证规则

- `template.json` 必须存在且可解析
- HTML 模板必须包含 `{{ resume.name }}` 和 `@page` CSS 规则

---

## 2.4 工具规范

### 2.4.1 内置工具规范

继承 `BaseTool`，需定义 `name`、`description`、`input_model`、`category`、`is_read_only_default`，实现 `execute()` 方法。

### 2.4.2 工具发现机制

1. **代码注册**：在 `_get_shared_tool_registry()` 中 `register()`
2. **目录扫描**：扫描 `tools/plugins/` 目录自动导入注册

---

## 2.5 提示词规范

### 2.5.1 文件结构

```
prompts/
├── system_prompt.md          # 系统提示词主模板
├── segments/                  # 分段模板
└── custom/                    # 用户自定义指令
    └── {user_id}/
        └── instructions.md
```

### 2.5.2 Token 预算管理

| 段落 | 预算 | 说明 |
|------|------|------|
| 角色定义 | 500 | 固定 |
| 输出格式 | 300 | 固定 |
| 工具描述 | 500 | 动态生成 |
| 用户记忆 | 2000 | 按 max_bytes 换算 |
| 通用技能 | 3000 | resume-skill.md |
| 行业技能 | 2000 | 动态加载 |
| JD 技能 | 1500 | 按需加载 |
| 用户自定义 | 500 | 用户指令 |
| **合计上限** | **~10000** | 超出按优先级截断 |

---

## 2.6 记忆文件规范

### 2.6.1 Front Matter 元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 记忆文件显示名称 |
| `writable` | bool | 是否允许 LLM 通过 `memory_write` 写入 |
| `max_size_kb` | int | 文件大小上限（KB） |
| `auto_created` | bool | 是否首次使用时自动创建 |
| `description` | string | 文件用途描述 |

- `WRITABLE_MEMORY_FILES` 从硬编码白名单改为读取 Front Matter 的 `writable` 字段
- `简历原文.md` 的 `writable: false`，其他文件 `writable: true`
