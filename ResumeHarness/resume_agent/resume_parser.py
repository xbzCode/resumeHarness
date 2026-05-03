"""Markdown → ResumeData 结构化解析器。

将 LLM 输出的 Markdown 格式简历解析为 ResumeData 对象。
对 LLM 输出格式不一致有容错能力，支持多种标题变体和格式偏差。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from resume_agent.models.resume_data import (
    ContactInfo,
    Education,
    ProjectExperience,
    ResumeData,
    SkillCategory,
    WorkExperience,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 章节标题别名映射
# ---------------------------------------------------------------------------

SECTION_ALIASES: dict[str, list[str]] = {
    "summary": [
        "个人简介",
        "个人总结",
        "自我介绍",
        "简介",
        "总结",
        "profile",
        "summary",
        "about",
    ],
    "experience": [
        "工作经历",
        "工作经验",
        "工作",
        "职业经历",
        "工作履历",
        "experience",
        "work experience",
        "employment",
    ],
    "education": [
        "教育背景",
        "教育经历",
        "教育",
        "学历",
        "学术背景",
        "education",
        "academic",
    ],
    "skills": [
        "专业技能",
        "技能",
        "核心技能",
        "技术栈",
        "技能标签",
        "skills",
        "technical skills",
        "competencies",
    ],
    "projects": [
        "项目经历",
        "项目经验",
        "项目",
        "核心项目",
        "重点项目",
        "projects",
        "project experience",
    ],
}

# 反向映射：别名 → 标准章节名
_ALIAS_TO_SECTION: dict[str, str] = {}
for section, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_SECTION[alias.lower()] = section


def _normalize_section_title(title: str) -> str | None:
    """将章节标题标准化为内部名称。

    输入如 "## 工作经历" 或 "## Work Experience" → 返回 "experience"
    """
    # 去掉 # 号和前后空白
    clean = re.sub(r"^#+\s*", "", title).strip()
    # 去掉可能的前导符号
    clean = clean.lstrip("▸►■●◆◇").strip()
    return _ALIAS_TO_SECTION.get(clean.lower())


# ---------------------------------------------------------------------------
# 联系方式解析
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(
    r"(?:\+?86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}"  # 中国手机号
    r"|"
    r"\d{3,4}[-\s]?\d{7,8}"  # 座机
)
_LOCATION_RE = re.compile(
    r"(北京|上海|广州|深圳|杭州|成都|南京|武汉|西安|重庆|苏州|天津|长沙|郑州|东莞|青岛|合肥|福州|厦门|济南|哈尔滨|沈阳|大连|昆明|贵阳|无锡|佛山|宁波|珠海|常州|温州|徐州|南通|嘉兴|太原|石家庄|兰州|南昌|长春|乌鲁木齐|呼和浩特)"
)
_WEBSITE_RE = re.compile(r"https?://[\w./\-?=&]+")
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)


def _parse_contact_line(text: str) -> ContactInfo:
    """从联系方式的原始文本行解析结构化联系方式。"""
    if not text:
        return ContactInfo()

    email_match = _EMAIL_RE.search(text)
    phone_match = _PHONE_RE.search(text)
    location_match = _LOCATION_RE.search(text)
    website_match = _WEBSITE_RE.search(text)
    linkedin_match = _LINKEDIN_RE.search(text)

    # 尝试提取微信
    wechat = None
    wechat_match = re.search(r"微信[：:]\s*(\S+)", text)
    if wechat_match:
        wechat = wechat_match.group(1)

    return ContactInfo(
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        location=location_match.group(0) if location_match else None,
        website=website_match.group(0) if website_match else None,
        linkedin=linkedin_match.group(0) if linkedin_match else None,
        wechat=wechat,
        raw_text=text.strip(),
    )


# ---------------------------------------------------------------------------
# 工作经历解析
# ---------------------------------------------------------------------------

_H3_TITLE_RE = re.compile(
    r"^(?P<title>.+?)\s*[-—–]\s*(?P<company>.+?)"
    r"(?:\s*[(\uff08]\s*(?P<period>[^)\uff09]+?)\s*[)\uff09]\s*)?$"
)


def _parse_experience_block(lines: list[str]) -> WorkExperience | None:
    """解析单个工作经历块（三级标题 + 列表项）。"""
    if not lines:
        return None

    # 第一行是三级标题
    title_line = lines[0]
    title_text = re.sub(r"^###\s*", "", title_line).strip()

    # 尝试解析 "职位 - 公司（时间段）" 格式
    match = _H3_TITLE_RE.match(title_text)

    if match:
        title = match.group("title").strip()
        company = match.group("company").strip()
        period = match.group("period") or ""
    else:
        # 容错：整行作为 title
        title = title_text
        company = ""
        period = ""

    # 提取列表项
    highlights: list[str] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        # 去掉列表标记
        item = re.sub(r"^[-*+]\s*", "", line)
        # 去掉粗体标记但保留文本
        item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
        item = item.strip()
        if item:
            highlights.append(item)

    return WorkExperience(
        title=title,
        company=company,
        period=period,
        highlights=highlights,
    )


# ---------------------------------------------------------------------------
# 教育背景解析
# ---------------------------------------------------------------------------

_EDU_TITLE_RE = re.compile(
    r"^(?P<degree>.+?)\s*[-—–]\s*(?P<major>.+?)\s*[-—–]\s*(?P<school>.+?)"
    r"(?:\s*[(\uff08]\s*(?P<period>[^)\uff09]+?)\s*[)\uff09]\s*)?$"
)


def _parse_education_block(lines: list[str]) -> Education | None:
    """解析单个教育背景块。"""
    if not lines:
        return None

    title_line = lines[0]
    title_text = re.sub(r"^###\s*", "", title_line).strip()

    match = _EDU_TITLE_RE.match(title_text)

    if match:
        degree = match.group("degree").strip()
        major = match.group("major").strip()
        school = match.group("school").strip()
        period = match.group("period") or ""
    else:
        # 容错：尝试更简单的格式
        parts = re.split(r"\s*[-—–]\s*", title_text)
        if len(parts) >= 2:
            degree = parts[0]
            major = parts[1] if len(parts) > 1 else ""
            school = parts[2] if len(parts) > 2 else major
            period = ""
        else:
            school = title_text
            degree = ""
            major = ""
            period = ""

    # 提取成就
    achievements: list[str] = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        item = re.sub(r"^[-*+]\s*", "", line)
        item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
        item = item.strip()
        if item:
            achievements.append(item)

    return Education(
        degree=degree,
        major=major,
        school=school,
        period=period,
        achievements=achievements,
    )


# ---------------------------------------------------------------------------
# 技能解析
# ---------------------------------------------------------------------------

_SKILL_CATEGORY_RE = re.compile(r"\*\*(.+?)\*\*[：:]\s*(.+)")


def _parse_skills_block(lines: list[str]) -> list[SkillCategory]:
    """解析技能章节。"""
    categories: list[SkillCategory] = []
    current_category: str | None = None
    current_skills: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 去掉列表标记
        item = re.sub(r"^[-*+]\s*", "", line)

        # 尝试匹配 "粗体类别：技能列表" 格式
        match = _SKILL_CATEGORY_RE.match(item)
        if match:
            # 保存上一个分类
            if current_category and current_skills:
                categories.append(
                    SkillCategory(category=current_category, skills=current_skills)
                )
            current_category = match.group(1).strip()
            skills_text = match.group(2).strip()
            # 用顿号、逗号、分号分割
            current_skills = re.split(r"[、，,；;]", skills_text)
            current_skills = [s.strip() for s in current_skills if s.strip()]
        else:
            # 可能是单独的技能项
            item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
            if item.strip():
                if current_category is None:
                    # 没有分类名，使用默认
                    current_category = "技能"
                current_skills.append(item.strip())

    # 保存最后一个分类
    if current_category and current_skills:
        categories.append(
            SkillCategory(category=current_category, skills=current_skills)
        )

    return categories


# ---------------------------------------------------------------------------
# 项目经历解析
# ---------------------------------------------------------------------------

_PROJECT_TITLE_RE = re.compile(
    r"^(?P<name>.+?)"
    r"(?:\s*[-—–]\s*(?P<role>.+?))?"
    r"(?:\s*[(\uff08]\s*(?P<period>[^)\uff09]+?)\s*[)\uff09]\s*)?$"
)

_PROJECT_DESC_RE = re.compile(r"\*\*项目描述\*\*[：:]\s*(.+)")
_PROJECT_CONTRIB_RE = re.compile(r"\*\*核心贡献\*\*[：:]\s*(.+)")


def _parse_project_block(lines: list[str]) -> ProjectExperience | None:
    """解析单个项目经历块。"""
    if not lines:
        return None

    title_line = lines[0]
    title_text = re.sub(r"^###\s*", "", title_line).strip()

    match = _PROJECT_TITLE_RE.match(title_text)
    if match:
        name = match.group("name").strip()
        role = match.group("role") or None
        period = match.group("period") or None
    else:
        name = title_text
        role = None
        period = None

    description: str | None = None
    contributions: list[str] = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        item = re.sub(r"^[-*+]\s*", "", line)

        # 尝试提取项目描述
        desc_match = _PROJECT_DESC_RE.match(item)
        if desc_match:
            description = desc_match.group(1).strip()
            continue

        # 尝试提取核心贡献（内联格式）
        contrib_match = _PROJECT_CONTRIB_RE.match(item)
        if contrib_match:
            text = contrib_match.group(1).strip()
            parts = re.split(r"[、，,；;]", text)
            contributions.extend(p.strip() for p in parts if p.strip())
            continue

        # 去掉粗体标记
        item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
        item = item.strip()
        if item:
            contributions.append(item)

    return ProjectExperience(
        name=name,
        role=role,
        period=period,
        description=description,
        contributions=contributions,
    )


# ---------------------------------------------------------------------------
# Markdown 分割与主解析函数
# ---------------------------------------------------------------------------


def _split_sections(markdown: str) -> dict[str, list[str]]:
    """按二级标题将 Markdown 分割为章节。

    Returns:
        章节名 → 行列表 的映射。特殊 key "__header__" 存放一级标题和联系方式。
    """
    lines = markdown.split("\n")
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in lines:
        # 检测一级标题（姓名）
        if re.match(r"^#\s+", line):
            current_section = "__header__"
            sections.setdefault(current_section, []).append(line)
            continue

        # 检测二级标题（章节）
        h2_match = re.match(r"^##\s+", line)
        if h2_match:
            section_key = _normalize_section_title(line)
            current_section = section_key or line.strip()
            sections.setdefault(current_section, []).append(line)
            continue

        # 其他行归入当前章节
        if current_section is not None:
            sections.setdefault(current_section, []).append(line)
        else:
            # 一级标题之前的行归入 header
            sections.setdefault("__header__", []).append(line)

    return sections


def _split_h3_blocks(lines: list[str]) -> list[list[str]]:
    """按三级标题将行列表分割为多个块。"""
    blocks: list[list[str]] = []
    current_block: list[str] = []

    for line in lines:
        if re.match(r"^###\s+", line):
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


def parse_markdown_to_resume_data(markdown_content: str) -> ResumeData:
    """将 LLM 输出的 Markdown 简历解析为结构化 ResumeData 对象。

    解析策略：
    1. 按 ## 二级标题分割章节（个人简介/工作经历/教育背景/专业技能/项目经历）
    2. 按三级标题 ### 分割条目（每个工作/教育/项目条目）
    3. 按列表项提取要点
    4. 联系方式从姓名下方的文本行解析
    5. 对格式不一致的 LLM 输出做容错处理

    Args:
        markdown_content: LLM 输出的 Markdown 简历内容

    Returns:
        ResumeData 结构化对象
    """
    sections = _split_sections(markdown_content)

    # --- 解析姓名和联系方式 ---
    name = ""
    contact = ContactInfo()
    header_lines = sections.get("__header__", [])

    for line in header_lines:
        # 一级标题是姓名
        h1_match = re.match(r"^#\s+(.+)$", line)
        if h1_match:
            name = h1_match.group(1).strip()
            # 去掉可能的粗体
            name = re.sub(r"\*\*(.+?)\*\*", r"\1", name)
            continue

        # 非标题行、非空行 → 可能是联系方式
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            contact = _parse_contact_line(stripped)

    # 如果一级标题没有找到，尝试从第一行提取
    if not name and header_lines:
        first_line = header_lines[0].strip()
        if first_line:
            name = re.sub(r"^#+\s*", "", first_line).strip()
            name = re.sub(r"\*\*(.+?)\*\*", r"\1", name)

    # --- 解析各章节 ---
    summary: str | None = None
    experience: list[WorkExperience] = []
    education: list[Education] = []
    skills: list[SkillCategory] = []
    projects: list[ProjectExperience] = []

    # 个人简介
    summary_lines = sections.get("summary", [])
    if summary_lines:
        summary_parts: list[str] = []
        for line in summary_lines:
            # 去掉二级标题行
            if re.match(r"^##\s+", line):
                continue
            stripped = line.strip()
            if stripped:
                summary_parts.append(stripped)
        if summary_parts:
            summary = " ".join(summary_parts)

    # 工作经历
    exp_lines = sections.get("experience", [])
    if exp_lines:
        # 跳过二级标题行，提取三级标题块
        exp_content = [l for l in exp_lines if not re.match(r"^##\s+", l)]
        for block in _split_h3_blocks(exp_content):
            # 跳过空块或只有空行的块
            if not block or all(not l.strip() for l in block):
                continue
            item = _parse_experience_block(block)
            if item and (item.title or item.company or item.highlights):
                experience.append(item)

        # 如果没有三级标题但有列表项，尝试整体解析
        if not experience and exp_content:
            # 容错：所有列表项合并为一个经历
            highlights = []
            for line in exp_content:
                stripped = line.strip()
                if stripped:
                    item = re.sub(r"^[-*+]\s*", "", stripped)
                    item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
                    if item:
                        highlights.append(item)
            if highlights:
                experience.append(
                    WorkExperience(
                        title="工作经历",
                        company="",
                        period="",
                        highlights=highlights,
                    )
                )

    # 教育背景
    edu_lines = sections.get("education", [])
    if edu_lines:
        edu_content = [l for l in edu_lines if not re.match(r"^##\s+", l)]
        for block in _split_h3_blocks(edu_content):
            if not block or all(not l.strip() for l in block):
                continue
            item = _parse_education_block(block)
            if item and (item.school or item.degree or item.achievements):
                education.append(item)

        # 容错：没有三级标题时整体解析
        if not education and edu_content:
            text = " ".join(l.strip() for l in edu_content)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            education.append(
                Education(
                    degree="",
                    major="",
                    school=text,
                    period="",
                )
            )

    # 专业技能
    skills_lines = sections.get("skills", [])
    if skills_lines:
        skills_content = [l for l in skills_lines if not re.match(r"^##\s+", l)]
        skills = _parse_skills_block(skills_content)

    # 项目经历
    proj_lines = sections.get("projects", [])
    if proj_lines:
        proj_content = [l for l in proj_lines if not re.match(r"^##\s+", l)]
        for block in _split_h3_blocks(proj_content):
            if not block or all(not l.strip() for l in block):
                continue
            item = _parse_project_block(block)
            if item and (item.name or item.contributions):
                projects.append(item)

    return ResumeData(
        name=name,
        contact=contact,
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
    )
