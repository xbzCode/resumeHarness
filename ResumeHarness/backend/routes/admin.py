"""工具/MCP/Skill/会话查询 API。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from resume_agent.config.settings import get_settings
from resume_agent.memory.paths import ensure_user_dirs
from resume_agent.services.session_storage import list_session_snapshots, load_latest_snapshot
from resume_agent.skills.resume_skill import get_skill_info, list_skills

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
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_model.model_json_schema(),
        })

    return {"tools": tools}


# ---------------------------------------------------------------------------
# MCP 状态 API
# ---------------------------------------------------------------------------

@router.get("/mcp/status")
async def mcp_status(request: Request) -> dict[str, Any]:
    """MCP 服务状态（P1 阶段暂返回配置信息）。"""
    settings = get_settings()
    servers = {}
    for name, config in settings.mcp_servers.items():
        servers[name] = {
            "type": config.type,
            "url": config.url,
            "status": "not_connected",  # P1 阶段未实际连接 MCP
        }

    return {
        "status": "available",
        "servers": servers,
        "message": "P1 阶段 MCP 未实际连接，仅返回配置信息",
    }


# ---------------------------------------------------------------------------
# Skill API
# ---------------------------------------------------------------------------

@router.get("/skills")
async def list_skills_api(request: Request) -> dict[str, Any]:
    """Skill 列表。"""
    skills = list_skills()
    return {"skills": skills}


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
