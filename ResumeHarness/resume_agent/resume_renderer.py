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
from typing import Any

from resume_agent.config.settings import get_settings
from resume_agent.exceptions import ResumeRenderError

log = logging.getLogger(__name__)

# 可用模板列表
AVAILABLE_TEMPLATES = ["professional", "academic", "creative"]

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
    """使用 Jinja2 模板渲染 ResumeData 为 HTML。"""
    from resume_agent.render_pdf_engine import render_resume_data_to_html
    return render_resume_data_to_html(resume_data, template)


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
    """同步简历索引到 SQLite 数据库。"""
    try:
        from resume_agent.db import get_db

        db = get_db()
        db.save_resume_index(
            user_id=user_id,
            resume_id=resume_id,
            file_path=file_path,
            size_bytes=size_bytes,
        )
    except Exception as exc:
        log.warning("同步简历索引到 SQLite 失败: %s", exc)
