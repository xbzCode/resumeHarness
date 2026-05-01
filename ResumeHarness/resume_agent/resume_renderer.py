"""Markdown → PDF/HTML 渲染，带渲染队列（同时仅 1 个渲染任务）。"""

from __future__ import annotations

import asyncio
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

def _markdown_to_html(markdown_content: str, template: str) -> str:
    """将 Markdown 转为带 CSS 模板的 HTML（用于 HTML 预览）。"""
    import markdown as md_lib

    # Markdown → HTML body
    html_body = md_lib.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    # 加载 CSS 模板
    css_path = Path(__file__).parent / "templates" / f"{template}.css"
    css_content = ""
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume</title>
<style>
{css_content}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    return html


async def _do_render(job: _RenderJob) -> bytes | str:
    """执行渲染。"""
    if job.output_format == "html":
        html = _markdown_to_html(job.markdown_content, job.template)
        return html

    if job.output_format == "pdf":
        async with _get_render_lock():
            # PDF 使用 fpdf2 直接从 Markdown 渲染（不需要先转 HTML）
            loop = asyncio.get_running_loop()
            pdf_bytes = await loop.run_in_executor(
                None, _render_pdf_sync, "", job.markdown_content, job.template,
            )
            return pdf_bytes

    if job.output_format == "markdown":
        return job.markdown_content

    raise ResumeRenderError(f"不支持的输出格式: {job.output_format}")


def _render_pdf_sync(html: str, markdown_content: str, template: str) -> bytes:
    """同步渲染 PDF（在线程池中执行）。

    使用 fpdf2 直接从 Markdown 渲染 PDF（中文支持好，无需系统 GTK 依赖）。
    """
    try:
        from resume_agent.render_pdf import render_markdown_to_pdf
    except ImportError:
        raise ResumeRenderError(
            "render_pdf 模块不可用"
        )

    pdf_bytes = render_markdown_to_pdf(markdown_content, template=template)
    return bytes(pdf_bytes)


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
        template: CSS 模板名称
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


def _generate_resume_id() -> str:
    """生成唯一的 resume_id。"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"resume_{ts}_{suffix}"


# ---------------------------------------------------------------------------
# 简历快照持久化
# ---------------------------------------------------------------------------

def save_resume_snapshot(
    user_id: str,
    markdown_content: str,
    resume_id: str | None = None,
) -> str:
    """保存简历快照到磁盘。

    存储路径: ~/.resume_agent/users/{user_id}/resumes/{resume_id}.md

    Returns:
        resume_id
    """
    settings = get_settings()
    resumes_dir = settings.get_user_resumes_dir(user_id)

    rid = resume_id or _generate_resume_id()
    path = resumes_dir / f"{rid}.md"
    path.write_text(markdown_content, encoding="utf-8")

    log.info("保存简历快照: user=%s resume_id=%s", user_id, rid)

    # 同步索引到 SQLite
    _sync_resume_index_to_db(
        user_id=user_id,
        resume_id=rid,
        file_path=str(path),
        size_bytes=path.stat().st_size,
    )

    # 清理超出数量限制的旧快照
    _cleanup_old_resumes(user_id)

    return rid


def load_resume_snapshot(user_id: str, resume_id: str) -> str | None:
    """加载简历快照内容。"""
    settings = get_settings()
    path = settings.get_user_resumes_dir(user_id) / f"{resume_id}.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
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
            # 从文件名提取 resume_id
            resume_id = path.stem
            snapshots.append({
                "resume_id": resume_id,
                "created_at": stat.st_mtime,
                "size_bytes": stat.st_size,
            })
        except OSError:
            continue
        if len(snapshots) >= limit:
            break

    return snapshots


def delete_resume_snapshot(user_id: str, resume_id: str) -> bool:
    """删除简历快照。"""
    settings = get_settings()
    path = settings.get_user_resumes_dir(user_id) / f"{resume_id}.md"
    if not path.exists():
        return False
    try:
        path.unlink()
        log.info("删除简历快照: user=%s resume_id=%s", user_id, resume_id)
        return True
    except OSError:
        return False


def _cleanup_old_resumes(user_id: str) -> None:
    """清理超出数量限制的旧简历快照。"""
    resumes = list_resume_snapshots(user_id, limit=MAX_RESUMES_PER_USER + 10)
    if len(resumes) <= MAX_RESUMES_PER_USER:
        return

    # 删除最旧的
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
