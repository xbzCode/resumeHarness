"""简历生成与下载 API。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from resume_agent.exceptions import ResumeNotFoundError, ResumeRenderError
from resume_agent.resume_renderer import (
    AVAILABLE_TEMPLATES,
    INDUSTRY_TEMPLATE_MAP,
    delete_resume_snapshot,
    detect_industry_from_text,
    get_template_hint,
    list_resume_snapshots,
    load_resume_data,
    load_resume_snapshot,
    render_resume,
    save_resume_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resume"])


def _get_user_id(request: Request) -> str:
    """获取当前用户 ID（从 JWT 认证中间件注入）。"""
    return request.state.user_id


@router.get("/resume/templates")
async def get_resume_templates() -> dict[str, Any]:
    """获取可用简历模板列表。"""
    return {
        "templates": [
            {
                "name": "professional",
                "label": "简洁商务",
                "description": "适用于互联网/科技行业",
            },
            {
                "name": "academic",
                "label": "学术风格",
                "description": "适用于高校/研究所",
            },
            {
                "name": "creative",
                "label": "创意排版",
                "description": "适用于设计/市场",
            },
        ]
    }


@router.get("/resume/template-hint")
async def get_template_hint_api(
    request: Request,
    jd: str | None = None,
    industry: str | None = None,
) -> dict[str, Any]:
    """根据岗位描述或行业推荐最佳简历模板。

    Args:
        jd: 岗位描述文本（URL encode），用于推断行业
        industry: 行业标识符（如 "tech"、"finance"），优先于 JD 推断

    Returns:
        推荐的模板名称、识别出的行业、行业→模板映射关系
    """
    # 推断行业
    detected_industry = industry
    if not detected_industry and jd:
        detected_industry = detect_industry_from_text(jd)

    # 获取模板推荐
    template = get_template_hint(industry=detected_industry, jd_text=jd)

    return {
        "template_hint": template,
        "detected_industry": detected_industry,
        "industry_template_map": INDUSTRY_TEMPLATE_MAP,
        "available_templates": AVAILABLE_TEMPLATES,
    }


@router.get("/resume/{resume_id}/download")
async def download_resume(
    resume_id: str,
    request: Request,
    format: str = "pdf",
    template: str = "professional",
) -> Response:
    """下载生成的简历（PDF/Markdown/HTML）。

    Args:
        resume_id: 简历 ID
        format: 输出格式 (pdf/markdown/html)
        template: CSS 模板（仅 pdf/html 有效）
    """
    user_id = _get_user_id(request)

    # 加载简历快照
    content = load_resume_snapshot(user_id, resume_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")

    if format == "markdown":
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{resume_id}.md"',
            },
        )

    try:
        result, _ = await render_resume(
            content,
            template=template,
            output_format=format,
            user_id=user_id,
            resume_id=resume_id,
        )
    except ResumeRenderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if format == "pdf":
        if not isinstance(result, bytes):
            raise HTTPException(status_code=500, detail="PDF 渲染结果异常")
        return Response(
            content=result,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{resume_id}.pdf"',
            },
        )

    if format == "html":
        return Response(
            content=result.encode("utf-8") if isinstance(result, str) else result,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{resume_id}.html"',
            },
        )

    raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")


@router.get("/resume/{resume_id}/preview")
async def preview_resume(
    resume_id: str,
    request: Request,
    template: str = "professional",
) -> Response:
    """预览简历内容（返回 HTML）。"""
    user_id = _get_user_id(request)

    content = load_resume_snapshot(user_id, resume_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")

    try:
        result, _ = await render_resume(
            content,
            template=template,
            output_format="html",
            user_id=user_id,
            resume_id=resume_id,
        )
    except ResumeRenderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    html = result if isinstance(result, str) else result.decode("utf-8")
    return Response(
        content=html.encode("utf-8"),
        media_type="text/html; charset=utf-8",
    )


@router.get("/resume")
async def list_resumes(request: Request, limit: int = 20) -> dict[str, Any]:
    """列出用户的简历快照。"""
    user_id = _get_user_id(request)
    snapshots = list_resume_snapshots(user_id, limit=limit)
    return {"resumes": snapshots}


@router.get("/resume/{resume_id}/data")
async def get_resume_data(resume_id: str, request: Request) -> dict[str, Any]:
    """获取简历结构化数据（ResumeData JSON）。

    用于前端组件渲染。如果 JSON 不存在，自动从 Markdown 解析。
    """
    user_id = _get_user_id(request)

    data = load_resume_data(user_id, resume_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")

    return {
        "resume_id": resume_id,
        "data": data,
        "available_templates": AVAILABLE_TEMPLATES,
    }


@router.delete("/resume/{resume_id}")
async def delete_resume(resume_id: str, request: Request) -> dict[str, Any]:
    """删除简历快照。"""
    user_id = _get_user_id(request)
    deleted = delete_resume_snapshot(user_id, resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")
    return {"deleted": True, "resume_id": resume_id}


@router.post("/resume/{resume_id}/score")
async def score_resume_api(
    resume_id: str,
    request: Request,
    jd: str | None = None,
) -> dict[str, Any]:
    """对简历进行多维度评分。

    Args:
        resume_id: 简历 ID
        jd: 可选的 JD 描述文本，用于关键词匹配评分
    """
    user_id = _get_user_id(request)

    # 加载简历数据
    data = load_resume_data(user_id, resume_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")

    try:
        from resume_agent.models.resume_data import ResumeData
        from resume_agent.services.resume_scorer import score_resume

        resume_data = ResumeData.model_validate(data)
        result = score_resume(resume_data, jd_text=jd)
        return {"resume_id": resume_id, **result.to_dict()}
    except Exception as exc:
        logger.error("简历评分失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"评分失败: {exc}")
