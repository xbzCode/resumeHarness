"""简历评分服务。

根据简历内容和可选的 JD 描述，从多维度评估简历质量并给出改进建议。

评分维度：
1. 结构完整性 — 简历是否包含必要章节
2. 内容充实度 — 各章节是否有足够内容
3. 量化数据 — 工作经历是否包含量化成果
4. 关键词匹配 — 与 JD 的关键词重叠度（需提供 JD）
5. 格式规范 — 是否遵循简历格式最佳实践
"""

from __future__ import annotations

import logging
import re
from typing import Any

from resume_agent.models.resume_data import ResumeData

logger = logging.getLogger(__name__)

# 评分权重
_WEIGHTS = {
    "structure": 0.20,  # 结构完整性
    "content": 0.25,    # 内容充实度
    "quantification": 0.20,  # 量化数据
    "keyword_match": 0.20,   # JD 关键词匹配
    "format": 0.15,     # 格式规范
}

# 必要章节
_REQUIRED_SECTIONS = ["summary", "experience", "education", "skills"]

# 推荐章节（加分项）
_OPTIONAL_SECTIONS = ["projects"]

# 量化指标正则：数字 + 单位/比例/排名
_QUANTIFICATION_PATTERNS = [
    re.compile(r"\d+%"),           # 百分比
    re.compile(r"\d+万"),           # 金额
    re.compile(r"\d+[万千百]"),     # 数量级
    re.compile(r"\d+\s*(人|个|次|项|名|台|套|份|篇|场)"),  # 量词
    re.compile(r"\d+\s*(万|千|百|十)"),     # 量级
    re.compile(r"[\d.]+\s*(倍|倍数)"),      # 倍数
    re.compile(r"(Top|top)\s*\d+"),         # 排名
    re.compile(r"第[一二三四五六七八九十\d]+"),  # 排名（中文）
    re.compile(r"\d+[.,]\d+"),              # 小数（通常表示比例/金额）
    re.compile(r"(节省|提高|降低|增长|提升|减少|缩短|优化).{0,10}\d+"),  # 动词+数字
]

# 格式问题检测
_FORMAT_ISSUES = {
    "long_paragraph": re.compile(r"[^\n]{300,}"),   # 过长段落
    "no_bullet": re.compile(r"^#{1,3}\s+.+\n[^-\*•]", re.MULTILINE),  # 章节下无列表
    "vague_word": re.compile(r"(参与|负责|协助|跟进|配合|推动|支持).{0,5}(工作|项目|任务|开发)"),  # 模糊表述
}


def _extract_jd_keywords(jd_text: str) -> set[str]:
    """从 JD 文本中提取关键词。"""
    if not jd_text:
        return set()

    # 常见技术关键词（含英文和中文）
    tech_pattern = re.compile(
        r"\b(?:"
        r"[A-Z][a-zA-Z0-9+#.]+(?:\.js|\.ts|\.py|\.go|\.rs)?"  # 编程语言/框架
        r"|(?:python|java|golang|rust|typescript|javascript|c\+\+|c#|ruby|php|swift|kotlin)"
        r"|(?:react|vue|angular|svelte|next\.js|nuxt)"
        r"|(?:docker|kubernetes|k8s|jenkins|gitlab|github)"
        r"|(?:mysql|postgresql|redis|mongodb|elasticsearch|kafka|rabbitmq)"
        r"|(?:aws|azure|gcp|阿里云|腾讯云)"
        r"|(?:linux|unix|shell|bash)"
        r"|(?:tensorflow|pytorch|onnx|langchain)"
        r")\b",
        re.IGNORECASE,
    )

    # 中文技能/资格关键词
    cn_skill_pattern = re.compile(
        r"(?:精通|熟练|熟悉|掌握|了解|具备)"
        r"(.{2,20}?)"
        r"(?:，|。|、|；|技能|能力|经验|背景|$)",
    )

    # 岗位要求关键词
    requirement_pattern = re.compile(
        r"(?:要求|需要|须|必须|应当|优先|加分|期望)"
        r"(.{2,30}?)"
        r"(?:，|。|、|；|$)",
    )

    keywords: set[str] = set()

    for m in tech_pattern.finditer(jd_text):
        kw = m.group(0).lower()
        if len(kw) >= 2:
            keywords.add(kw)

    for m in cn_skill_pattern.finditer(jd_text):
        kw = m.group(1).strip()
        if 2 <= len(kw) <= 20:
            keywords.add(kw)

    for m in requirement_pattern.finditer(jd_text):
        kw = m.group(1).strip()
        if 2 <= len(kw) <= 20:
            keywords.add(kw)

    return keywords


def _count_quantification(text: str) -> int:
    """统计文本中包含量化数据的条目数。"""
    count = 0
    for pattern in _QUANTIFICATION_PATTERNS:
        count += len(pattern.findall(text))
    return count


def _score_structure(resume_data: ResumeData) -> tuple[float, list[str]]:
    """评分：结构完整性。"""
    score = 0.0
    issues: list[str] = []

    # 检查必要章节
    section_map = {
        "summary": resume_data.summary,
        "experience": resume_data.experience,
        "education": resume_data.education,
        "skills": resume_data.skills,
    }

    present_count = 0
    for section_name, content in section_map.items():
        if content:
            present_count += 1
        else:
            issues.append(f"缺少「{_section_cn(section_name)}」章节")

    # 必要章节评分（4 个必要章节，每个 20 分，满分 80）
    score = (present_count / len(_REQUIRED_SECTIONS)) * 80

    # 加分项（项目经历，满分 20）
    if resume_data.projects:
        score += 20
    else:
        issues.append("建议添加「项目经历」章节，展示具体项目成果")

    return min(score, 100), issues


def _score_content(resume_data: ResumeData) -> tuple[float, list[str]]:
    """评分：内容充实度。"""
    score = 0.0
    issues: list[str] = []

    # 个人简介（满分 25）
    if resume_data.summary:
        summary_len = len(resume_data.summary)
        if summary_len >= 50:
            score += 25
        elif summary_len >= 20:
            score += 15
            issues.append("个人简介偏短，建议补充更多细节")
        else:
            score += 5
            issues.append("个人简介过短，建议写 50 字以上")
    else:
        issues.append("缺少个人简介")

    # 工作经历（满分 40）
    if resume_data.experience:
        avg_highlights = sum(len(exp.highlights) for exp in resume_data.experience) / len(resume_data.experience)
        if avg_highlights >= 4:
            score += 40
        elif avg_highlights >= 2:
            score += 25
            issues.append("工作经历要点偏少，建议每段经历写 3-5 条核心成果")
        else:
            score += 10
            issues.append("工作经历过于简略，每段应至少 3 条要点")
    else:
        issues.append("缺少工作经历")

    # 技能（满分 20）
    if resume_data.skills:
        total_skills = sum(len(cat.skills) for cat in resume_data.skills)
        if total_skills >= 8:
            score += 20
        elif total_skills >= 4:
            score += 12
            issues.append("技能标签偏少，建议列出 8 项以上核心技能")
        else:
            score += 5
            issues.append("技能标签过少，建议分类列出更多相关技能")
    else:
        issues.append("缺少专业技能")

    # 教育背景（满分 15）
    if resume_data.education:
        score += 15
    else:
        issues.append("缺少教育背景")

    return min(score, 100), issues


def _score_quantification(resume_data: ResumeData) -> tuple[float, list[str]]:
    """评分：量化数据占比。"""
    issues: list[str] = []

    if not resume_data.experience:
        return 0, ["无工作经历，无法评估量化数据"]

    total_highlights = 0
    quantified_highlights = 0

    for exp in resume_data.experience:
        for highlight in exp.highlights:
            total_highlights += 1
            if _count_quantification(highlight) > 0:
                quantified_highlights += 1

    if total_highlights == 0:
        return 10, ["工作经历无要点，建议添加核心成果"]

    ratio = quantified_highlights / total_highlights

    if ratio >= 0.6:
        score = 90 + min(ratio - 0.6, 0.4) * 25  # 90-100
    elif ratio >= 0.3:
        score = 60 + (ratio - 0.3) / 0.3 * 30  # 60-90
    elif ratio >= 0.1:
        score = 30 + (ratio - 0.1) / 0.2 * 30  # 30-60
    else:
        score = ratio / 0.1 * 30  # 0-30
        issues.append("工作经历中量化数据极少，建议用具体数字描述成果（如"提升 30%"、"节省 50 万"）")

    if 0.1 <= ratio < 0.6:
        issues.append(f"仅 {int(ratio*100)}% 的成果要点包含量化数据，建议提高至 60% 以上")

    return min(score, 100), issues


def _score_keyword_match(
    resume_data: ResumeData, jd_keywords: set[str]
) -> tuple[float, list[str]]:
    """评分：JD 关键词匹配度。"""
    if not jd_keywords:
        # 无 JD 时不参与评分，返回中间分
        return 70, ["未提供 JD，无法评估关键词匹配度"]

    issues: list[str] = []

    # 从简历中提取所有文本
    resume_text_parts: list[str] = []
    if resume_data.summary:
        resume_text_parts.append(resume_data.summary)
    for exp in resume_data.experience:
        resume_text_parts.append(f"{exp.title} {exp.company}")
        resume_text_parts.extend(exp.highlights)
    for cat in resume_data.skills:
        resume_text_parts.extend(cat.skills)
    for proj in resume_data.projects:
        resume_text_parts.append(f"{proj.name} {proj.description or ''}")
        resume_text_parts.extend(proj.contributions)

    resume_text_lower = " ".join(resume_text_parts).lower()

    # 匹配关键词
    matched: set[str] = set()
    unmatched: set[str] = set()

    for kw in jd_keywords:
        if kw.lower() in resume_text_lower:
            matched.add(kw)
        else:
            unmatched.add(kw)

    if not jd_keywords:
        return 50, issues

    match_ratio = len(matched) / len(jd_keywords)

    if match_ratio >= 0.7:
        score = 85 + min(match_ratio - 0.7, 0.3) * 50  # 85-100
    elif match_ratio >= 0.4:
        score = 55 + (match_ratio - 0.4) / 0.3 * 30  # 55-85
    elif match_ratio >= 0.2:
        score = 30 + (match_ratio - 0.2) / 0.2 * 25  # 30-55
    else:
        score = match_ratio / 0.2 * 30  # 0-30

    # 报告未匹配的关键词（取前 5 个）
    if unmatched:
        top_unmatched = sorted(unmatched)[:5]
        issues.append(f"以下 JD 关键词未在简历中出现：{', '.join(top_unmatched)}")

    if match_ratio < 0.7:
        issues.append(f"关键词匹配度 {int(match_ratio*100)}%，建议将匹配度提升至 70% 以上")

    return min(score, 100), issues


def _score_format(resume_data: ResumeData) -> tuple[float, list[str]]:
    """评分：格式规范。"""
    score = 70.0  # 基础分
    issues: list[str] = []

    # 检查联系方式
    contact = resume_data.contact
    if not contact.email and not contact.phone and not contact.raw_text:
        score -= 15
        issues.append("缺少联系方式（邮箱或电话）")

    # 检查姓名
    if not resume_data.name or len(resume_data.name.strip()) < 2:
        score -= 10
        issues.append("姓名信息不完整")

    # 检查工作经历格式
    for exp in resume_data.experience:
        if not exp.period:
            score -= 5
            issues.append(f"「{exp.title}」缺少时间段")

        # 检查模糊表述
        for highlight in exp.highlights:
            if _FORMAT_ISSUES["vague_word"].search(highlight):
                score -= 2
                issues.append(f"存在模糊表述："参与/负责…工作"，建议改为具体行动+成果")
                break  # 每段经历只报一次

    # 检查时间段格式（粗略检查）
    for exp in resume_data.experience:
        if exp.period and not re.search(r"\d{4}", exp.period):
            score -= 3
            issues.append("时间段格式不规范，建议使用 YYYY.MM - YYYY.MM")

    return max(score, 0), issues


def _section_cn(section: str) -> str:
    """章节英文名转中文。"""
    return {
        "summary": "个人简介",
        "experience": "工作经历",
        "education": "教育背景",
        "skills": "专业技能",
        "projects": "项目经历",
    }.get(section, section)


class ResumeScoreResult:
    """简历评分结果。"""

    def __init__(
        self,
        overall_score: float,
        dimensions: dict[str, float],
        suggestions: list[str],
        jd_keywords_matched: list[str] | None = None,
        jd_keywords_missing: list[str] | None = None,
    ) -> None:
        self.overall_score = round(overall_score, 1)
        self.dimensions = {k: round(v, 1) for k, v in dimensions.items()}
        self.suggestions = suggestions
        self.jd_keywords_matched = jd_keywords_matched or []
        self.jd_keywords_missing = jd_keywords_missing or []

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "suggestions": self.suggestions,
            "jd_keywords_matched": self.jd_keywords_matched,
            "jd_keywords_missing": self.jd_keywords_missing,
        }


def score_resume(
    resume_data: ResumeData,
    jd_text: str | None = None,
) -> ResumeScoreResult:
    """对简历进行多维度评分。

    Args:
        resume_data: 简历结构化数据
        jd_text: 可选的 JD 描述文本

    Returns:
        ResumeScoreResult 评分结果
    """
    # 提取 JD 关键词
    jd_keywords = _extract_jd_keywords(jd_text) if jd_text else set()

    # 各维度评分
    structure_score, structure_issues = _score_structure(resume_data)
    content_score, content_issues = _score_content(resume_data)
    quant_score, quant_issues = _score_quantification(resume_data)
    keyword_score, keyword_issues = _score_keyword_match(resume_data, jd_keywords)
    format_score, format_issues = _score_format(resume_data)

    dimensions = {
        "structure": structure_score,
        "content": content_score,
        "quantification": quant_score,
        "keyword_match": keyword_score,
        "format": format_score,
    }

    # 加权总分
    overall = sum(
        dimensions[dim] * _WEIGHTS[dim]
        for dim in dimensions
    )

    # 合并改进建议（去重，最多 8 条）
    all_issues = structure_issues + content_issues + quant_issues + keyword_issues + format_issues
    seen = set()
    unique_issues: list[str] = []
    for issue in all_issues:
        if issue not in seen:
            seen.add(issue)
            unique_issues.append(issue)
    suggestions = unique_issues[:8]

    # JD 关键词匹配情况
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    if jd_keywords:
        resume_text_lower = _get_resume_full_text(resume_data).lower()
        for kw in jd_keywords:
            if kw.lower() in resume_text_lower:
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)

    return ResumeScoreResult(
        overall_score=overall,
        dimensions=dimensions,
        suggestions=suggestions,
        jd_keywords_matched=matched_keywords[:10],
        jd_keywords_missing=missing_keywords[:10],
    )


def _get_resume_full_text(resume_data: ResumeData) -> str:
    """获取简历全部文本（用于关键词匹配）。"""
    parts: list[str] = []
    if resume_data.name:
        parts.append(resume_data.name)
    if resume_data.summary:
        parts.append(resume_data.summary)
    for exp in resume_data.experience:
        parts.append(f"{exp.title} {exp.company} {exp.period}")
        parts.extend(exp.highlights)
    for edu in resume_data.education:
        parts.append(f"{edu.degree} {edu.major} {edu.school}")
        parts.extend(edu.achievements)
    for cat in resume_data.skills:
        parts.append(cat.category)
        parts.extend(cat.skills)
    for proj in resume_data.projects:
        parts.append(f"{proj.name} {proj.role or ''} {proj.description or ''}")
        parts.extend(proj.contributions)
    return " ".join(parts)
