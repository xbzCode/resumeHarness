"""简历渲染管线：Markdown → ResumeData → Jinja2 HTML 模板 → PDF/HTML。

支持双格式快照持久化（ResumeData JSON + Markdown 原文），
通过 SSE resume_data 事件推送结构化数据到前端组件渲染。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from resume_agent.config.settings import get_settings
from resume_agent.exceptions import ResumeRenderError

log = logging.getLogger(__name__)

# 可用模板列表
AVAILABLE_TEMPLATES = ["professional", "academic", "creative", "minimal", "elegant", "tech", "compact"]


def get_available_templates() -> list[str]:
    """获取可用模板列表（从注册表动态发现）。"""
    from resume_agent.templates.registry import list_templates
    return [t["name"] for t in list_templates() if t.get("has_html")]

# 行业→模板推荐映射
# 根据行业/岗位特征推荐最合适的简历模板
INDUSTRY_TEMPLATE_MAP: dict[str, str] = {
    "tech": "professional",       # 互联网/科技 → 商务双栏
    "internet": "professional",   # 互联网 → 商务双栏
    "finance": "elegant",         # 金融 → 优雅
    "banking": "elegant",         # 银行 → 优雅
    "education": "academic",      # 教育 → 学术单栏
    "academic": "academic",       # 学术 → 学术单栏
    "design": "creative",         # 设计 → 创意卡片
    "marketing": "creative",      # 市场/营销 → 创意卡片
    "media": "creative",          # 媒体 → 创意卡片
    "healthcare": "academic",     # 医疗 → 学术单栏
    "government": "academic",     # 政府/公共事业 → 学术单栏
    "manufacturing": "professional",  # 制造业 → 商务双栏
    "consulting": "elegant",      # 咨询 → 优雅
    "legal": "academic",          # 法律 → 学术单栏
    "startup": "minimal",         # 初创 → 极简
    "foreign": "minimal",         # 外企 → 极简
    "engineer": "tech",           # 工程师 → 科技
}

# 岗位关键词→行业映射
# 用于从 JD 或简历内容中推断所属行业
JOB_KEYWORD_INDUSTRIES: dict[str, str] = {
    # 互联网/科技
    "前端": "tech", "后端": "tech", "全栈": "tech", "算法": "tech",
    "开发": "tech", "架构": "tech", "测试": "tech", "运维": "tech",
    "SRE": "tech", "DevOps": "tech", "数据": "tech", "AI": "tech",
    "机器学习": "tech", "深度学习": "tech", "NLP": "tech", "CV": "tech",
    "产品经理": "tech", "程序员": "tech", "工程师": "tech",
    "React": "tech", "Vue": "tech", "Java": "tech", "Python": "tech",
    "Go": "tech", "TypeScript": "tech", "Kubernetes": "tech",
    # 金融
    "风控": "finance", "信贷": "finance", "合规": "finance",
    "投行": "finance", "证券": "finance", "基金": "finance",
    "精算": "finance", "CFA": "finance", "CPA": "finance", "FRM": "finance",
    "银行": "finance", "保险": "finance", "资管": "finance",
    "交易": "finance", "清算": "finance", "KYC": "finance", "AML": "finance",
    # 教育
    "教师": "education", "教授": "education", "讲师": "education",
    "教研": "education", "课程": "education", "教学": "education",
    "K12": "education", "高校": "education", "学术": "education",
    # 设计/市场
    "设计师": "design", "UI": "design", "UX": "design",
    "视觉": "design", "交互": "design", "品牌": "marketing",
    "运营": "marketing", "市场": "marketing", "营销": "marketing",
    "增长": "marketing", "广告": "marketing", "PR": "marketing",
    # 医疗
    "医生": "healthcare", "临床": "healthcare", "护士": "healthcare",
    "医药": "healthcare", "医疗": "healthcare", "GMP": "healthcare",
    # 制造
    "生产": "manufacturing", "工艺": "manufacturing", "供应链": "manufacturing",
    "质量": "manufacturing", "MES": "manufacturing", "ERP": "manufacturing",
    # 法律
    "律师": "legal", "法务": "legal", "合规审查": "legal",
    # 咨询
    "咨询": "consulting", "顾问": "consulting", "战略": "consulting",
}

# 渲染超时（秒）
RENDER_TIMEOUT = 60

# 单用户最大简历快照数
MAX_RESUMES_PER_USER = 20


# ---------------------------------------------------------------------------
# 渲染队列：同时仅允许 1 个 weasyprint 渲染任务
# ---------------------------------------------------------------------------

_render_lock: asyncio.Lock | None = None
_render_queue: asyncio.Queue[_RenderJob] | None = None
_render_task: asyncio.Task | None = None


def _get_render_lock() -> asyncio.Lock:
    global _render_lock
    if _render_lock is None:
        _render_lock = asyncio.Lock()
    return _render_lock


def _get_render_queue() -> asyncio.Queue[_RenderJob]:
    global _render_queue
    if _render_queue is None:
        _render_queue = asyncio.Queue()
    return _render_queue


class _RenderJob:
    """渲染任务。"""

    def __init__(
        self,
        markdown_content: str,
        template: str,
        output_format: str,
        user_id: str,
        resume_id: str,
    ) -> None:
        self.markdown_content = markdown_content
        self.template = template
        self.output_format = output_format
        self.user_id = user_id
        self.resume_id = resume_id
        self.future: asyncio.Future[bytes | str] = asyncio.get_running_loop().create_future()


async def _render_worker() -> None:
    """后台渲染工作协程。"""
    queue = _get_render_queue()
    while True:
        job = await queue.get()
        try:
            result = await asyncio.wait_for(
                _do_render(job),
                timeout=RENDER_TIMEOUT,
            )
            job.future.set_result(result)
        except Exception as exc:
            if not job.future.done():
                job.future.set_exception(exc)
        finally:
            queue.task_done()


async def _ensure_render_worker() -> None:
    """确保渲染工作协程已启动。"""
    global _render_task
    if _render_task is None or _render_task.done():
        _render_task = asyncio.create_task(_render_worker())


# ---------------------------------------------------------------------------
# 渲染实现
# ---------------------------------------------------------------------------

def _parse_resume_data(markdown_content: str) -> Any:
    """将 Markdown 解析为 ResumeData，解析失败返回 None。"""
    try:
        from resume_agent.resume_parser import parse_markdown_to_resume_data
        data = parse_markdown_to_resume_data(markdown_content)
        if data.has_content():
            return data
    except Exception as exc:
        log.warning("ResumeData 解析失败: %s", exc)
    return None


def _render_html_from_resume_data(resume_data: Any, template: str) -> str:
    """使用 Jinja2 模板渲染 ResumeData 为 HTML（带页面居中样式）。"""
    return render_resume_data_to_html_with_center(resume_data, template)


def render_resume_data_to_html_with_center(resume_data: Any, template: str) -> str:
    """使用 Jinja2 模板渲染 ResumeData 为 HTML，并添加页面居中样式。

    用于 HTML 预览/分享端点，PDF 渲染不使用此函数。
    """
    from resume_agent.render_pdf_engine import render_resume_data_to_html
    html = render_resume_data_to_html(resume_data, template)
    # 在 </style> 前注入居中样式（仅 HTML 预览/分享，不影响 PDF 渲染）
    center_css = """
body {
    display: flex;
    justify-content: center;
    background: #f5f5f5;
    padding: 20px 0;
}
"""
    html = html.replace("</style>", center_css + "\n</style>", 1)
    return html


def _render_html_from_markdown(markdown_content: str, template: str) -> str:
    """使用 python-markdown + CSS 渲染 HTML（降级路径）。"""
    import markdown as md_lib

    from resume_agent.render_pdf_engine import _load_css_template, _get_font_family_css

    html_body = md_lib.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    css_content = _load_css_template(template)
    font_css = _get_font_family_css()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume</title>
<style>
{font_css}
{css_content}
body {{
    display: flex;
    justify-content: center;
    background: #f5f5f5;
    padding: 20px 0;
}}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


async def _do_render(job: _RenderJob) -> bytes | str:
    """执行渲染。"""
    if job.output_format == "html":
        # 优先使用 ResumeData + Jinja2 模板
        resume_data = _parse_resume_data(job.markdown_content)
        if resume_data:
            return _render_html_from_resume_data(resume_data, job.template)
        # 降级到 python-markdown + CSS
        return _render_html_from_markdown(job.markdown_content, job.template)

    if job.output_format == "pdf":
        async with _get_render_lock():
            loop = asyncio.get_running_loop()
            pdf_bytes = await loop.run_in_executor(
                None, _render_pdf_sync, job.markdown_content, job.template,
            )
            return pdf_bytes

    if job.output_format == "markdown":
        return job.markdown_content

    raise ResumeRenderError(f"不支持的输出格式: {job.output_format}")


def _render_pdf_sync(markdown_content: str, template: str) -> bytes:
    """同步渲染 PDF（在线程池中执行）。

    优先使用结构化渲染（ResumeData + Jinja2），失败时降级到 Markdown 渲染。
    """
    try:
        from resume_agent.render_pdf_engine import render_resume_data_to_pdf

        resume_data = _parse_resume_data(markdown_content)
        if resume_data:
            pdf_bytes = render_resume_data_to_pdf(resume_data, template)
            return bytes(pdf_bytes)
    except Exception as exc:
        log.warning("结构化 PDF 渲染失败，降级到 Markdown 渲染: %s", exc)

    # 降级到旧的 Markdown → PDF 路径
    try:
        from resume_agent.render_pdf_engine import render_markdown_to_pdf
        pdf_bytes = render_markdown_to_pdf(markdown_content, template=template)
        return bytes(pdf_bytes)
    except ImportError:
        raise ResumeRenderError("render_pdf_engine 模块不可用")


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

async def render_resume(
    markdown_content: str,
    *,
    template: str = "professional",
    output_format: str = "pdf",
    user_id: str = "",
    resume_id: str | None = None,
) -> tuple[bytes | str, str]:
    """渲染简历，返回 (渲染结果, resume_id)。

    Args:
        markdown_content: Markdown 格式的简历内容
        template: 模板名称
        output_format: 输出格式 (pdf/html/markdown)
        user_id: 用户 ID
        resume_id: 简历 ID，为空时自动生成

    Returns:
        (渲染结果, resume_id)
    """
    if template not in AVAILABLE_TEMPLATES:
        raise ResumeRenderError(f"不支持的模板: {template}，可用模板: {AVAILABLE_TEMPLATES}")

    rid = resume_id or _generate_resume_id()

    await _ensure_render_worker()

    job = _RenderJob(
        markdown_content=markdown_content,
        template=template,
        output_format=output_format,
        user_id=user_id,
        resume_id=rid,
    )
    await _get_render_queue().put(job)

    try:
        result = await job.future
    except asyncio.TimeoutError:
        raise ResumeRenderError(f"简历渲染超时（{RENDER_TIMEOUT}s）")
    except Exception as exc:
        raise ResumeRenderError(f"简历渲染失败: {exc}") from exc

    return result, rid


def parse_resume_data_from_markdown(markdown_content: str) -> dict[str, Any] | None:
    """将 Markdown 解析为 ResumeData 并返回可序列化的字典。

    用于 SSE resume_data 事件推送。

    Args:
        markdown_content: Markdown 格式的简历内容

    Returns:
        ResumeData 字典，解析失败返回 None
    """
    resume_data = _parse_resume_data(markdown_content)
    if resume_data is None:
        return None
    return resume_data.model_dump()


def _generate_resume_id() -> str:
    """生成唯一的 resume_id。"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"resume_{ts}_{suffix}"


# ---------------------------------------------------------------------------
# 简历快照持久化（双格式：JSON + Markdown）
# ---------------------------------------------------------------------------

def save_resume_snapshot(
    user_id: str,
    markdown_content: str,
    resume_id: str | None = None,
) -> str:
    """保存简历快照到磁盘（双格式：ResumeData JSON + Markdown 原文）。

    存储路径:
    - ~/.resume_agent/users/{user_id}/resumes/{resume_id}.json  (ResumeData JSON)
    - ~/.resume_agent/users/{user_id}/resumes/{resume_id}.md    (Markdown 原文)

    Returns:
        resume_id
    """
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    rid = resume_id or _generate_resume_id()

    # 保存 Markdown 原文
    md_path = resumes_dir / f"{rid}.md"
    md_path.write_text(markdown_content, encoding="utf-8")

    # 解析并保存 ResumeData JSON
    resume_data = _parse_resume_data(markdown_content)
    if resume_data:
        json_path = resumes_dir / f"{rid}.json"
        json_content = resume_data.model_dump_json(indent=2)
        json_path.write_text(json_content, encoding="utf-8")
        log.info("保存简历快照(双格式): user=%s resume_id=%s", user_id, rid)
    else:
        log.warning("ResumeData 解析失败，仅保存 Markdown: user=%s resume_id=%s", user_id, rid)

    # 同步索引到 SQLite
    _sync_resume_index_to_db(
        user_id=user_id,
        resume_id=rid,
        file_path=str(md_path),
        size_bytes=md_path.stat().st_size,
    )

    # 清理超出数量限制的旧快照
    _cleanup_old_resumes(user_id)

    return rid


def load_resume_snapshot(user_id: str, resume_id: str) -> str | None:
    """加载简历快照内容（Markdown 格式）。"""
    settings = get_settings()
    path = settings.get_user_resumes_dir(user_id) / f"{resume_id}.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def save_resume_data(user_id: str, resume_id: str, data: dict[str, Any]) -> bool:
    """保存用户编辑后的 ResumeData JSON 到磁盘。

    同时重新生成 Markdown 原文，保持双格式一致。

    Args:
        user_id: 用户 ID
        resume_id: 简历 ID
        data: ResumeData 字典

    Returns:
        是否保存成功
    """
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    json_path = resumes_dir / f"{resume_id}.json"
    md_path = resumes_dir / f"{resume_id}.md"

    # 校验简历存在
    if not json_path.exists() and not md_path.exists():
        log.warning("简历不存在，无法保存: user=%s resume_id=%s", user_id, resume_id)
        return False

    # 校验 ResumeData 格式
    try:
        from resume_agent.models.resume_data import ResumeData

        resume_data = ResumeData.model_validate(data)
    except Exception as exc:
        log.error("ResumeData 校验失败: %s", exc)
        return False

    # 保存 JSON
    json_content = resume_data.model_dump_json(indent=2)
    json_path.write_text(json_content, encoding="utf-8")

    # 重新生成 Markdown 并保存
    md_content = _resume_data_to_markdown(resume_data)
    md_path.write_text(md_content, encoding="utf-8")

    log.info("保存用户编辑的简历数据: user=%s resume_id=%s", user_id, resume_id)
    return True


def _resume_data_to_markdown(data: "ResumeData") -> str:
    """将 ResumeData 转换为 Markdown 格式。

    用于前端编辑后重新生成 Markdown，保持双格式一致。
    支持 section_order 自定义章节顺序。
    """
    lines: list[str] = []

    # 姓名
    if data.name:
        lines.append(f"# {data.name}")
        lines.append("")

    # 联系方式
    contact_parts: list[str] = []
    if data.contact.email:
        contact_parts.append(data.contact.email)
    if data.contact.phone:
        contact_parts.append(data.contact.phone)
    if data.contact.location:
        contact_parts.append(data.contact.location)
    if data.contact.website:
        contact_parts.append(data.contact.website)
    if data.contact.linkedin:
        contact_parts.append(data.contact.linkedin)
    if data.contact.wechat:
        contact_parts.append(f"微信: {data.contact.wechat}")
    if data.contact.raw_text and not contact_parts:
        contact_parts.append(data.contact.raw_text)
    if contact_parts:
        lines.append(" | ".join(contact_parts))
        lines.append("")

    # 按 section_order 顺序渲染各章节
    default_order = ["summary", "experience", "education", "skills", "projects"]
    section_order = data.section_order if data.section_order else default_order

    # 构建各章节内容
    section_builders: dict[str, Callable[[], list[str]]] = {
        "summary": _build_summary_section,
        "experience": _build_experience_section,
        "education": _build_education_section,
        "skills": _build_skills_section,
        "projects": _build_projects_section,
    }

    rendered_keys: set[str] = set()
    for key in section_order:
        if key in rendered_keys:
            continue
        if key in section_builders:
            section_lines = section_builders[key](data)
            if section_lines:
                lines.extend(section_lines)
            rendered_keys.add(key)

    # 渲染 section_order 中未包含但有内容的章节
    for key in default_order:
        if key not in rendered_keys and key in section_builders:
            section_lines = section_builders[key](data)
            if section_lines:
                lines.extend(section_lines)

    return "\n".join(lines)


def _build_summary_section(data: "ResumeData") -> list[str]:
    """构建个人简介章节。"""
    if not data.summary:
        return []
    return ["## 个人简介", "", data.summary, ""]


def _build_experience_section(data: "ResumeData") -> list[str]:
    """构建工作经历章节。"""
    if not data.experience:
        return []
    lines = ["## 工作经历", ""]
    for exp in data.experience:
        lines.append(f"### {exp.title} - {exp.company}（{exp.period}）")
        lines.append("")
        for h in exp.highlights:
            lines.append(f"- {h}")
        lines.append("")
    return lines


def _build_education_section(data: "ResumeData") -> list[str]:
    """构建教育背景章节。"""
    if not data.education:
        return []
    lines = ["## 教育背景", ""]
    for edu in data.education:
        lines.append(f"### {edu.degree} - {edu.major} - {edu.school}（{edu.period}）")
        lines.append("")
        for a in edu.achievements:
            lines.append(f"- {a}")
        if edu.achievements:
            lines.append("")
    return lines


def _build_skills_section(data: "ResumeData") -> list[str]:
    """构建专业技能章节。"""
    if not data.skills:
        return []
    lines = ["## 专业技能", ""]
    for cat in data.skills:
        lines.append(f"- **{cat.category}**：{'、'.join(cat.skills)}")
    lines.append("")
    return lines


def _build_projects_section(data: "ResumeData") -> list[str]:
    """构建项目经历章节。"""
    if not data.projects:
        return []
    lines = ["## 项目经历", ""]
    for proj in data.projects:
        header = f"### {proj.name}"
        if proj.role:
            header += f" - {proj.role}"
        if proj.period:
            header += f"（{proj.period}）"
        lines.append(header)
        lines.append("")
        if proj.description:
            lines.append(f"- **项目描述**：{proj.description}")
        for c in proj.contributions:
            lines.append(f"- {c}")
        lines.append("")
    return lines


def load_resume_data(user_id: str, resume_id: str) -> dict[str, Any] | None:
    """加载简历快照的结构化数据（ResumeData JSON）。

    如果 JSON 文件不存在，尝试从 Markdown 解析。
    """
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    # 优先加载 JSON
    json_path = resumes_dir / f"{resume_id}.json"
    if json_path.exists():
        try:
            raw = json_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("加载 ResumeData JSON 失败: %s", exc)

    # 降级：从 Markdown 解析
    md_content = load_resume_snapshot(user_id, resume_id)
    if md_content:
        return parse_resume_data_from_markdown(md_content)

    return None


def list_resume_snapshots(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """列出用户的简历快照。"""
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    snapshots: list[dict[str, Any]] = []
    for path in sorted(
        resumes_dir.glob("resume_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            stat = path.stat()
            resume_id = path.stem
            # 检查是否有对应的 JSON 文件
            has_json = (resumes_dir / f"{resume_id}.json").exists()
            snapshots.append({
                "resume_id": resume_id,
                "created_at": stat.st_mtime,
                "size_bytes": stat.st_size,
                "has_structured_data": has_json,
            })
        except OSError:
            continue
        if len(snapshots) >= limit:
            break

    return snapshots


def delete_resume_snapshot(user_id: str, resume_id: str) -> bool:
    """删除简历快照（同时删除 .md 和 .json）。"""
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    deleted = False
    for ext in [".md", ".json"]:
        path = resumes_dir / f"{resume_id}{ext}"
        if path.exists():
            try:
                path.unlink()
                deleted = True
            except OSError:
                pass

    if deleted:
        log.info("删除简历快照: user=%s resume_id=%s", user_id, resume_id)
    return deleted


def _cleanup_old_resumes(user_id: str) -> None:
    """清理超出数量限制的旧简历快照。"""
    resumes = list_resume_snapshots(user_id, limit=MAX_RESUMES_PER_USER + 10)
    if len(resumes) <= MAX_RESUMES_PER_USER:
        return

    to_delete = resumes[MAX_RESUMES_PER_USER:]
    for snap in to_delete:
        delete_resume_snapshot(user_id, snap["resume_id"])


def _sync_resume_index_to_db(
    *,
    user_id: str,
    resume_id: str,
    file_path: str,
    size_bytes: int,
) -> None:
    """同步简历索引到 SQLite 数据库（异步，fire-and-forget）。"""
    import asyncio

    async def _do_sync() -> None:
        try:
            from resume_agent.db import get_db

            db = await get_db()
            await db.save_resume_index(
                user_id=user_id,
                resume_id=resume_id,
                file_path=file_path,
                size_bytes=size_bytes,
            )
        except Exception as exc:
            log.warning("同步简历索引到 SQLite 失败: %s", exc)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_do_sync())
    except RuntimeError:
        # 没有运行中的事件循环，跳过
        pass


# ---------------------------------------------------------------------------
# 行业识别与模板推荐
# ---------------------------------------------------------------------------

def detect_industry_from_text(text: str) -> str | None:
    """从文本（JD 或简历内容）中识别行业类型。

    通过关键词匹配推断最可能的行业。

    Args:
        text: JD 或简历的文本内容

    Returns:
        行业标识符（如 "tech"、"finance"），无法识别时返回 None
    """
    if not text:
        return None

    text_lower = text.lower()
    industry_scores: dict[str, int] = {}

    for keyword, industry in JOB_KEYWORD_INDUSTRIES.items():
        # 不区分大小写匹配
        count = text_lower.count(keyword.lower())
        if count > 0:
            industry_scores[industry] = industry_scores.get(industry, 0) + count

    if not industry_scores:
        return None

    # 返回得分最高的行业
    best_industry = max(industry_scores, key=industry_scores.get)  # type: ignore[arg-type]
    return best_industry


def get_template_hint(industry: str | None = None, jd_text: str | None = None) -> str:
    """根据行业或 JD 内容推荐最佳简历模板。

    优先级：
    1. 直接传入的 industry 参数
    2. 从 jd_text 推断的行业
    3. 默认返回 "professional"

    Args:
        industry: 行业标识符（如 "tech"、"finance"），可选
        jd_text: JD 文本内容，用于推断行业，可选

    Returns:
        推荐的模板名称
    """
    # 优先使用直接传入的行业
    effective_industry = industry

    # 如果没有直接传入行业，尝试从 JD 推断
    if not effective_industry and jd_text:
        effective_industry = detect_industry_from_text(jd_text)

    # 根据行业映射返回模板
    if effective_industry and effective_industry in INDUSTRY_TEMPLATE_MAP:
        return INDUSTRY_TEMPLATE_MAP[effective_industry]

    # 默认返回商务模板
    return "professional"


def get_industry_skill_name(industry: str | None = None, jd_text: str | None = None) -> str | None:
    """根据行业或 JD 内容推荐应加载的行业技能文件名。

    从技能文件的 Front Matter `industry` 字段自动构建映射，
    不再硬编码行业→技能文件映射。

    Args:
        industry: 行业标识符（如 "tech"、"finance"），可选
        jd_text: JD 文本内容，用于推断行业，可选

    Returns:
        技能文件名（不含 .md 后缀），如 "resume-tech"，无匹配时返回 None
    """
    from resume_agent.skills.resume_skill import get_industry_skill_map

    industry_skill_map = get_industry_skill_map()

    effective_industry = industry

    if not effective_industry and jd_text:
        effective_industry = detect_industry_from_text(jd_text)

    if effective_industry and effective_industry in industry_skill_map:
        skill_names = industry_skill_map[effective_industry]
        if skill_names:
            return skill_names[0]  # 返回第一个匹配的技能

    return None
