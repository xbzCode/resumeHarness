"""简历生成与下载 API。"""

from __future__ import annotations

import logging
import uuid
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
    render_resume_data_to_html_with_center,
    save_resume_data,
    save_resume_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resume"])


def _get_user_id(request: Request) -> str:
    """获取当前用户 ID（从 JWT 认证中间件注入）。"""
    return request.state.user_id


@router.get("/resume/templates")
async def get_resume_templates() -> dict[str, Any]:
    """获取可用简历模板列表（从注册表动态发现）。"""
    from resume_agent.templates.registry import list_templates

    templates = list_templates()
    return {
        "templates": [
            {
                "name": t["name"],
                "label": t.get("display_name", t["name"]),
                "description": t.get("description", ""),
                "version": t.get("version", "1.0.0"),
                "layout": t.get("layout", ""),
                "recommended_industries": t.get("recommended_industries", []),
                "color_scheme": t.get("color_scheme", {}),
                "has_preview": t.get("has_preview", False),
            }
            for t in templates
            if t.get("has_html")
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

    if format == "docx":
        # 使用 python-docx 生成，不走 render_resume
        resume_data_dict = load_resume_data(user_id, resume_id)
        if resume_data_dict is None:
            raise HTTPException(status_code=404, detail=f"简历结构化数据不存在: {resume_id}")
        try:
            from resume_agent.models.resume_data import ResumeData
            from resume_agent.render_docx import render_resume_data_to_docx

            resume_data = ResumeData.model_validate(resume_data_dict)
            docx_bytes = render_resume_data_to_docx(resume_data, template=template)
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=f"DOCX 渲染依赖未安装: {exc}")
        except Exception as exc:
            logger.error("DOCX 渲染失败: %s", exc)
            raise HTTPException(status_code=500, detail=f"DOCX 渲染失败: {exc}")

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{resume_id}.docx"',
            },
        )

    # PDF/HTML: 优先使用 ResumeData JSON（保留编辑后的数据如 section_order），
    # JSON 不存在时降级到 Markdown 渲染
    resume_data_dict = load_resume_data(user_id, resume_id)
    if resume_data_dict is not None:
        try:
            from resume_agent.models.resume_data import ResumeData

            resume_data = ResumeData.model_validate(resume_data_dict)

            if format == "pdf":
                from resume_agent.render_pdf_engine import render_resume_data_to_pdf
                result = render_resume_data_to_pdf(resume_data, template)
                return Response(
                    content=result,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="{resume_id}.pdf"',
                    },
                )

            if format == "html":
                from resume_agent.resume_renderer import render_resume_data_to_html_with_center
                html = render_resume_data_to_html_with_center(resume_data, template)
                return Response(
                    content=html.encode("utf-8"),
                    media_type="text/html; charset=utf-8",
                    headers={
                        "Content-Disposition": f'inline; filename="{resume_id}.html"',
                    },
                )
        except Exception as exc:
            logger.warning("从 ResumeData JSON 渲染失败，降级到 Markdown 渲染: %s", exc)

    # 降级：从 Markdown 渲染
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

    # 优先从 ResumeData JSON 渲染
    resume_data_dict = load_resume_data(user_id, resume_id)
    if resume_data_dict is not None:
        try:
            from resume_agent.models.resume_data import ResumeData
            resume_data = ResumeData.model_validate(resume_data_dict)
            html = render_resume_data_to_html_with_center(resume_data, template)
            return Response(
                content=html.encode("utf-8"),
                media_type="text/html; charset=utf-8",
            )
        except Exception as exc:
            logger.warning("从 ResumeData JSON 预览失败，降级到 Markdown: %s", exc)

    # 降级
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


@router.put("/resume/{resume_id}/data")
async def update_resume_data(
    resume_id: str,
    request: Request,
) -> dict[str, Any]:
    """更新简历结构化数据（前端编辑后保存）。

    Request Body:
        ResumeData JSON 对象

    Returns:
        更新结果
    """
    user_id = _get_user_id(request)

    # 读取请求体
    body = await request.json()
    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 ResumeData JSON 对象")

    # 保存
    success = save_resume_data(user_id, resume_id, body)
    if not success:
        raise HTTPException(status_code=404, detail=f"简历不存在或数据格式错误: {resume_id}")

    # 返回更新后的数据
    updated_data = load_resume_data(user_id, resume_id)
    return {
        "resume_id": resume_id,
        "data": updated_data,
        "updated": True,
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


# ---------------------------------------------------------------------------
# 分享链接 API
# ---------------------------------------------------------------------------


@router.post("/resume/{resume_id}/share")
async def create_share_link(
    resume_id: str,
    request: Request,
) -> dict[str, Any]:
    """生成或重新生成简历分享链接。

    每份简历只有一个有效分享链接，重新生成会使旧链接失效。
    返回分享 URL。
    """
    user_id = _get_user_id(request)

    # 校验简历存在
    data = load_resume_data(user_id, resume_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"简历不存在: {resume_id}")

    from resume_agent.db import get_db
    db = await get_db()

    share_id = await db.create_share_link(
        resume_id=resume_id,
        user_id=user_id,
    )

    return {
        "share_id": share_id,
        "share_url": f"/api/share/{share_id}",
    }


@router.get("/resume/{resume_id}/share")
async def get_share_link(
    resume_id: str,
    request: Request,
) -> dict[str, Any]:
    """获取简历的分享链接信息。"""
    user_id = _get_user_id(request)

    from resume_agent.db import get_db
    db = await get_db()

    link = await db.get_share_link_by_resume(user_id, resume_id)
    if link is None:
        return {"share_id": None, "share_url": None}

    return {
        "share_id": link["share_id"],
        "share_url": f"/api/share/{link['share_id']}",
        "created_at": link["created_at"],
    }


@router.delete("/resume/{resume_id}/share")
async def delete_share_link(
    resume_id: str,
    request: Request,
) -> dict[str, Any]:
    """撤销简历分享链接。"""
    user_id = _get_user_id(request)

    from resume_agent.db import get_db
    db = await get_db()

    link = await db.get_share_link_by_resume(user_id, resume_id)
    if link is None:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    await db.delete_share_link(link["share_id"])
    return {"deleted": True}


# ---------------------------------------------------------------------------
# 公开分享访问（无需认证）
# ---------------------------------------------------------------------------


@router.get("/share/{share_id}")
async def access_shared_resume(
    share_id: str,
    format: str = "html",
    template: str | None = None,
) -> Response:
    """通过分享链接访问简历（无需认证）。

    Args:
        share_id: 分享 UUID
        format: 输出格式 (html/pdf/markdown/docx)
        template: 模板名称（可选，默认使用分享时保存的模板）
    """
    from resume_agent.db import get_db
    db = await get_db()

    link = await db.get_share_link(share_id)
    if link is None:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    resume_id = link["resume_id"]
    user_id = link["user_id"]
    effective_template = template or link.get("template", "professional")

    # 加载简历快照
    content = load_resume_snapshot(user_id, resume_id)
    if content is None:
        raise HTTPException(status_code=404, detail="简历不存在")

    if format == "markdown":
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
        )

    # PDF/HTML/DOCX: 优先使用 ResumeData JSON
    resume_data_dict = load_resume_data(user_id, resume_id)

    if format == "html":
        if resume_data_dict is not None:
            try:
                from resume_agent.models.resume_data import ResumeData
                resume_data = ResumeData.model_validate(resume_data_dict)
                html = render_resume_data_to_html_with_center(resume_data, effective_template)
                return Response(
                    content=html.encode("utf-8"),
                    media_type="text/html; charset=utf-8",
                )
            except Exception as exc:
                logger.warning("从 ResumeData JSON 渲染 HTML 失败，降级到 Markdown: %s", exc)
        try:
            result, _ = await render_resume(
                content,
                template=effective_template,
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

    if format == "pdf":
        if resume_data_dict is not None:
            try:
                from resume_agent.models.resume_data import ResumeData
                from resume_agent.render_pdf_engine import render_resume_data_to_pdf
                resume_data = ResumeData.model_validate(resume_data_dict)
                result = render_resume_data_to_pdf(resume_data, effective_template)
                return Response(
                    content=result,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'inline; filename="{resume_id}.pdf"',
                    },
                )
            except Exception as exc:
                logger.warning("从 ResumeData JSON 渲染 PDF 失败，降级到 Markdown: %s", exc)
        try:
            result, _ = await render_resume(
                content,
                template=effective_template,
                output_format="pdf",
                user_id=user_id,
                resume_id=resume_id,
            )
        except ResumeRenderError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        return Response(
            content=result,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{resume_id}.pdf"',
            },
        )

    if format == "docx":
        if resume_data_dict is None:
            raise HTTPException(status_code=404, detail="简历结构化数据不存在")

        try:
            from resume_agent.models.resume_data import ResumeData
            from resume_agent.render_docx import render_resume_data_to_docx

            resume_data = ResumeData.model_validate(resume_data_dict)
            docx_bytes = render_resume_data_to_docx(resume_data, template=effective_template)
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=f"DOCX 渲染依赖未安装: {exc}")
        except Exception as exc:
            logger.error("DOCX 渲染失败: %s", exc)
            raise HTTPException(status_code=500, detail=f"DOCX 渲染失败: {exc}")

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{resume_id}.docx"',
            },
        )

    raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")
