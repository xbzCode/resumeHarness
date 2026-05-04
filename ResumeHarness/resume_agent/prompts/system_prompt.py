"""简历 Agent 系统提示词模板与组装逻辑。"""

from __future__ import annotations

from pathlib import Path

from resume_agent.config.settings import get_settings

# ---------------------------------------------------------------------------
# 基础角色提示词
# ---------------------------------------------------------------------------


def _load_prompt_template() -> str:
    """从 prompts/system_prompt.md 加载系统提示词模板。

    如果文件不存在，回退到空字符串。
    """
    template_path = Path(__file__).parent / "system_prompt.md"
    if template_path.exists():
        try:
            return template_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return ""


RESUME_AGENT_SYSTEM_PROMPT = _load_prompt_template()


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
    from resume_agent.skills.resume_skill import load_skill_content
    return load_skill_content("resume-skill")


def load_industry_skill(skill_name: str) -> str | None:
    """加载指定行业技能文件。

    Args:
        skill_name: 技能文件名（不含 .md 后缀），如 "resume-tech"

    Returns:
        技能文件正文内容，文件不存在时返回 None
    """
    from resume_agent.skills.resume_skill import load_skill_content
    return load_skill_content(skill_name)


def load_jd_skill() -> str | None:
    """加载 JD 解析技能文件。"""
    from resume_agent.skills.resume_skill import load_skill_content
    return load_skill_content("resume-jd")


def load_user_instructions(user_id: str) -> str | None:
    """加载用户自定义指令。

    从用户记忆目录的 custom_instructions.md 读取。
    """
    settings = get_settings()
    memory_dir = settings.get_user_memory_dir(user_id)
    instructions_path = memory_dir / "custom_instructions.md"
    return _read_file_safe(instructions_path, max_bytes=settings.memory_other_max_bytes)


async def build_resume_system_prompt(
    user_id: str,
    latest_user_prompt: str | None = None,
) -> str:
    """构建简历 Agent 的系统提示词，注入用户专属记忆。

    提示词组装顺序：
    1. 基础角色提示词（从 system_prompt.md 加载）
    2. 用户专属记忆
    3. 通用简历技能（resume-skill.md）
    4. 行业特定技能（根据用户最新 prompt 推断行业，动态加载）
    5. JD 解析技能（resume-jd.md）
    6. 用户自定义指令
    """
    # 1. 基础角色提示词
    parts = [RESUME_AGENT_SYSTEM_PROMPT]

    # 2. 加载用户记忆文件
    memory_texts = load_memory_documents(user_id)
    if memory_texts:
        parts.append("\n## 用户专属记忆\n" + memory_texts)

    # 3. 加载 resume-skill.md（通用技能）
    skill_text = load_resume_skill()
    if skill_text:
        parts.append("\n## 简历优化技能指南\n" + skill_text)

    # 4. 根据用户最新 prompt 推断行业，动态加载行业技能
    if latest_user_prompt:
        from resume_agent.resume_renderer import get_industry_skill_name, detect_industry_from_text

        industry = detect_industry_from_text(latest_user_prompt)
        skill_name = get_industry_skill_name(industry=industry)
        if skill_name:
            industry_skill_text = load_industry_skill(skill_name)
            if industry_skill_text:
                industry_label = industry or skill_name.replace("resume-", "")
                parts.append(f"\n## {industry_label}行业专项技能\n" + industry_skill_text)

    # 5. 加载 JD 解析技能
    jd_skill_text = load_jd_skill()
    if jd_skill_text:
        parts.append("\n## JD 解析技能指南\n" + jd_skill_text)

    # 6. 用户自定义指令
    user_instructions = load_user_instructions(user_id)
    if user_instructions:
        parts.append("\n## 用户自定义规则\n" + user_instructions)

    return "\n".join(parts)
