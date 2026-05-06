"""工具/MCP/Skill/会话查询 API。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from resume_agent.config.settings import get_settings
from resume_agent.memory.paths import ensure_user_dirs
from resume_agent.services.session_storage import list_session_snapshots, load_latest_snapshot, delete_session_snapshot
from resume_agent.skills.resume_skill import get_skill_info, list_skills, load_skill_content

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


def _get_user_id(request: Request) -> str:
    """获取当前用户 ID（从 JWT 认证中间件注入）。"""
    return request.state.user_id


# ---------------------------------------------------------------------------
# 工具 API
# ---------------------------------------------------------------------------

@router.get("/tools")
async def list_tools(request: Request) -> dict[str, Any]:
    """查询可用工具列表。"""
    from resume_agent.runtime import _get_shared_tool_registry

    registry = _get_shared_tool_registry()
    tools = []
    for tool in registry.list_tools():
        tool_info = {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_model.model_json_schema(),
            "category": getattr(tool, "category", "其他"),
            "is_read_only": tool.is_read_only(None),
            "source": "mcp" if tool.name.startswith("mcp__") else "builtin",
        }
        tools.append(tool_info)

    # 按分类分组统计
    categories: dict[str, int] = {}
    for t in tools:
        cat = t["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {"tools": tools, "total": len(tools), "categories": categories}


# ---------------------------------------------------------------------------
# MCP 状态 API
# ---------------------------------------------------------------------------

@router.get("/mcp/status")
async def mcp_status(request: Request) -> dict[str, Any]:
    """MCP 服务状态。"""
    try:
        from resume_agent.mcp.manager import get_mcp_manager

        manager = get_mcp_manager()
        return manager.get_status()
    except Exception as exc:
        logger.warning("获取 MCP 状态失败: %s", exc)
        # 降级：返回配置信息
        settings = get_settings()
        servers = {}
        for name, config in settings.mcp_servers.items():
            servers[name] = {
                "url": config.url,
                "connected": False,
                "tools": [],
                "reason": str(exc),
            }
        return {
            "initialized": False,
            "total_servers": len(servers),
            "connected_servers": 0,
            "servers": servers,
        }


@router.post("/mcp/refresh")
async def mcp_refresh(request: Request) -> dict[str, Any]:
    """刷新 MCP 连接和工具列表。"""
    try:
        from resume_agent.mcp.manager import get_mcp_manager
        from resume_agent.runtime import _get_shared_tool_registry

        manager = get_mcp_manager()

        # 重新初始化连接
        await manager.shutdown()
        await manager.initialize()

        # 刷新工具注册
        tool_registry = _get_shared_tool_registry()
        count = manager.register_tools_to_registry(tool_registry)

        return {
            "success": True,
            "registered_tools": count,
            "status": manager.get_status(),
        }
    except Exception as exc:
        logger.error("刷新 MCP 失败: %s", exc)
        return {
            "success": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# MCP 认证 API
# ---------------------------------------------------------------------------

@router.get("/mcp/auth/{server_name}")
async def get_mcp_auth(server_name: str, request: Request) -> dict[str, Any]:
    """获取用户级 MCP 认证信息。"""
    user_id = _get_user_id(request)
    from resume_agent.mcp_auth import load_user_mcp_auth

    headers = load_user_mcp_auth(user_id, server_name)
    # 隐藏敏感值
    masked_headers = {}
    for key, value in headers.items():
        if any(kw in key.lower() for kw in ("authorization", "password", "secret", "token", "key")):
            masked_headers[key] = "****" if value else ""
        else:
            masked_headers[key] = value

    return {
        "server_name": server_name,
        "headers": masked_headers,
        "has_auth": bool(headers),
    }


@router.put("/mcp/auth/{server_name}")
async def update_mcp_auth(server_name: str, request: Request) -> dict[str, Any]:
    """更新用户级 MCP 认证信息。"""
    user_id = _get_user_id(request)
    body = await request.json()
    headers = body.get("headers", {})

    if not isinstance(headers, dict):
        return {"success": False, "error": "headers 必须为字典"}

    from resume_agent.mcp_auth import save_user_mcp_auth

    save_user_mcp_auth(user_id, server_name, headers)
    return {"success": True, "server_name": server_name}


@router.delete("/mcp/auth/{server_name}")
async def delete_mcp_auth_api(server_name: str, request: Request) -> dict[str, Any]:
    """删除用户级 MCP 认证信息。"""
    user_id = _get_user_id(request)
    from resume_agent.mcp_auth import delete_user_mcp_auth

    deleted = delete_user_mcp_auth(user_id, server_name)
    return {"success": deleted, "server_name": server_name}


# ---------------------------------------------------------------------------
# Skill API
# ---------------------------------------------------------------------------

@router.get("/skills")
async def list_skills_api(request: Request) -> dict[str, Any]:
    """Skill 列表。"""
    skills = list_skills()
    return {"skills": skills}


@router.get("/skills/{skill_name}")
async def get_skill_detail(skill_name: str) -> dict[str, Any]:
    """获取指定 Skill 的详情。"""
    info = get_skill_info(skill_name)
    if not info.get("found"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")
    return info


@router.get("/skills/{skill_name}/content")
async def get_skill_content(skill_name: str) -> dict[str, Any]:
    """获取指定 Skill 的正文内容（不含 Front Matter）。"""
    content = load_skill_content(skill_name)
    if content is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 不存在")
    return {"name": skill_name, "content": content}


# ---------------------------------------------------------------------------
# 会话 API
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(request: Request, limit: int = 20) -> dict[str, Any]:
    """列出用户历史会话。"""
    user_id = _get_user_id(request)
    ensure_user_dirs(user_id)
    sessions = list_session_snapshots(user_id, limit=limit)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    """加载历史会话详情。"""
    user_id = _get_user_id(request)
    settings = get_settings()
    from pathlib import Path

    session_path = settings.get_user_sessions_dir(user_id) / f"session-{session_id}.json"
    if not session_path.exists():
        return {"session_id": session_id, "found": False}

    try:
        import json
        data = json.loads(session_path.read_text(encoding="utf-8"))
        return {
            "session_id": session_id,
            "found": True,
            "summary": data.get("summary", ""),
            "model": data.get("model", ""),
            "message_count": data.get("message_count", 0),
            "created_at": data.get("created_at", 0),
            "messages": data.get("messages", []),
        }
    except Exception as exc:
        logger.error("加载会话失败: %s", exc)
        return {"session_id": session_id, "found": False, "error": str(exc)}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request) -> dict[str, Any]:
    """删除历史会话。"""
    user_id = _get_user_id(request)
    ensure_user_dirs(user_id)
    deleted = delete_session_snapshot(user_id, session_id)
    if deleted:
        return {"session_id": session_id, "deleted": True}
    return {"session_id": session_id, "deleted": False}


# ---------------------------------------------------------------------------
# 速率限制 API
# ---------------------------------------------------------------------------

@router.get("/rate-limit/status")
async def rate_limit_status(request: Request) -> dict[str, Any]:
    """获取当前用户的速率限制状态。"""
    user_id = _get_user_id(request)
    settings = get_settings()

    if not settings.rate_limit_enabled:
        return {
            "enabled": False,
            "user_id": user_id,
        }

    # 从 app 获取 RateLimitMiddleware 实例
    from backend.app import get_rate_limit_middleware
    middleware = get_rate_limit_middleware()

    if middleware is None:
        return {
            "enabled": True,
            "user_id": user_id,
            "rpm_limit": settings.rate_limit_rpm,
            "status": "not_initialized",
        }

    limiter = middleware.get_limiter()
    return {
        "enabled": True,
        **limiter.get_status(user_id),
    }


# ---------------------------------------------------------------------------
# 监控 API
# ---------------------------------------------------------------------------

@router.get("/monitor/metrics")
async def monitor_metrics(request: Request) -> dict[str, Any]:
    """获取监控指标（需认证）。"""
    from backend.app import get_monitoring_middleware
    middleware = get_monitoring_middleware()

    if middleware is None:
        return {"enabled": False}

    return {
        "enabled": True,
        **middleware.get_metrics(),
    }
