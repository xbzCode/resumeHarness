"""简历 Agent 系统提示词模板与组装逻辑。"""

from __future__ import annotations

from pathlib import Path

from resume_agent.config.settings import get_settings

# ---------------------------------------------------------------------------
# 基础角色提示词
# ---------------------------------------------------------------------------

RESUME_AGENT_SYSTEM_PROMPT = """\
# 角色定义

你是一位专业的简历优化顾问（Resume Agent）。你的核心职责是根据用户提供的简历内容和目标岗位需求，\
帮助用户生成高质量、匹配岗位的优化简历。

## 核心能力

1. **简历分析与优化**：分析用户现有简历的不足，提出针对性改进建议
2. **岗位匹配**：根据 JD（职位描述）调整简历内容，突出匹配的关键词和经验
3. **结构化输出**：以 Markdown 格式输出结构清晰的简历内容
4. **记忆积累**：通过 memory_write 工具记录用户的偏好和反馈，后续对话自动遵循

## 输出格式

生成简历时，请使用以下 Markdown 结构：

```markdown
# 姓名

## 个人简介
[1-2 句话的个人简介]

## 工作经历

### 公司名称 | 职位 | 时间段
- **成果描述**：使用 STAR 法则描述，量化成果
- **核心贡献**：突出与目标岗位匹配的技能和经验

## 教育背景

### 学校名称 | 专业 | 学位 | 时间段

## 技能标签
- 技能1、技能2、技能3...

## 项目经历（如有）

### 项目名称 | 角色 | 时间段
- **项目描述**：简述项目背景
- **核心贡献**：量化成果
```

## 工作原则

- 始终以 Markdown 格式输出简历内容
- 优先使用用户记忆中的偏好和风格
- 当用户表达求职偏好时，主动调用 memory_write 持久化
- 每次生成简历后，调用 memory_write 记录优化历史
- 如用户提供了 JD 链接，使用 web_fetch 抓取并分析岗位需求

## 工具使用规范

- **web_fetch**：仅用于抓取用户提供的**外部网页 URL**（如招聘网站 JD 链接）。不要用 web_fetch 访问任何不存在的、虚构的或内部路径的 URL。**重要**：如果用户已在对话中直接提供了岗位描述或 JD 内容，不要重复调用 web_fetch，直接使用用户提供的文本即可。
- **memory_write**：用于将用户偏好、技能标签、优化历史等信息写入本地记忆文件。记录优化历史时使用 memory_write(doc_name="优化历史.md", ...)，切勿使用 web_fetch。当用户提供了 JD 内容时，应通过 memory_write 写入记忆以便后续会话使用。
"""


# ---------------------------------------------------------------------------
# 提示词组装
# ---------------------------------------------------------------------------

def _read_file_safe(path: Path, max_bytes: int = 16384) -> str | None:
    """安全读取文件内容，限制最大字节数。"""
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            return None
        if len(content.encode("utf-8")) > max_bytes:
            # 简单截断
            content = content[:max_bytes]
        return content
    except OSError:
        return None


def load_memory_documents(user_id: str) -> str:
    """加载用户记忆文件内容，组装为提示词片段。"""
    settings = get_settings()
    memory_dir = settings.get_user_memory_dir(user_id)

    parts: list[str] = []
    for md_file in sorted(memory_dir.glob("*.md")):
        content = _read_file_safe(md_file, max_bytes=settings.memory_other_max_bytes)
        if content:
            parts.append(f"### {md_file.name}\n```\n{content}\n```")

    return "\n\n".join(parts)


def load_resume_skill() -> str | None:
    """加载 resume-skill.md 领域技能文件。"""
    # 从包内 skills 目录加载
    skill_path = Path(__file__).parent.parent / "skills" / "resume-skill.md"
    return _read_file_safe(skill_path, max_bytes=32000)


async def build_resume_system_prompt(
    user_id: str,
    latest_user_prompt: str | None = None,
) -> str:
    """构建简历 Agent 的系统提示词，注入用户专属记忆。"""
    # 1. 基础角色提示词
    parts = [RESUME_AGENT_SYSTEM_PROMPT]

    # 2. 加载用户记忆文件
    memory_texts = load_memory_documents(user_id)
    if memory_texts:
        parts.append("\n## 用户专属记忆\n" + memory_texts)

    # 3. 加载 resume-skill.md
    skill_text = load_resume_skill()
    if skill_text:
        parts.append("\n## 简历优化技能指南\n" + skill_text)

    return "\n".join(parts)
