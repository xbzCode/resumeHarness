"""用户级 MCP 认证动态注入。

ToolRegistry 为进程级单例，工具定义全局共享。
但部分 MCP 工具（如邮件发送）需要按用户传入不同的认证信息。

解决方案：
  1. ToolRegistry 查找工具定义（全局共享）
  2. 执行层从用户上下文获取该用户对应的 MCP headers/auth token
  3. 合并全局配置 + 用户级认证信息，发起 MCP 调用
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from resume_agent.config.settings import get_settings

log = logging.getLogger(__name__)


def get_user_mcp_dir(user_id: str) -> Path:
    """获取用户级 MCP 认证信息存储目录。"""
    settings = get_settings()
    mcp_dir = settings.get_user_dir(user_id) / "mcp_auth"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    return mcp_dir


def load_user_mcp_auth(user_id: str, server_name: str) -> dict[str, str]:
    """加载用户级 MCP 认证信息。

    返回 headers dict，如 {"Authorization": "Bearer xxx"}。
    """
    mcp_dir = get_user_mcp_dir(user_id)
    auth_path = mcp_dir / f"{server_name}.json"

    if not auth_path.exists():
        return {}

    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
        return data.get("headers", {})
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("加载用户 MCP 认证失败 user=%s server=%s: %s", user_id, server_name, exc)
        return {}


def save_user_mcp_auth(
    user_id: str,
    server_name: str,
    headers: dict[str, str],
) -> Path:
    """保存用户级 MCP 认证信息。"""
    mcp_dir = get_user_mcp_dir(user_id)
    auth_path = mcp_dir / f"{server_name}.json"

    data = {"headers": headers}
    auth_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("保存用户 MCP 认证: user=%s server=%s", user_id, server_name)
    return auth_path


def delete_user_mcp_auth(user_id: str, server_name: str) -> bool:
    """删除用户级 MCP 认证信息。"""
    mcp_dir = get_user_mcp_dir(user_id)
    auth_path = mcp_dir / f"{server_name}.json"

    if not auth_path.exists():
        return False

    try:
        auth_path.unlink()
        log.info("删除用户 MCP 认证: user=%s server=%s", user_id, server_name)
        return True
    except OSError:
        return False


async def get_mcp_headers(tool_name: str, user_id: str) -> dict[str, str]:
    """获取 MCP 工具调用时的 headers，合并全局 + 用户级认证。

    Args:
        tool_name: MCP 工具名称（如 "mcp__email__send"）
        user_id: 用户 ID

    Returns:
        合并后的 headers dict
    """
    settings = get_settings()

    # 从工具名提取 server_name（格式: mcp__{server}__{method}）
    server_name = _extract_server_name(tool_name)

    # 全局 headers
    global_headers: dict[str, str] = {}
    if server_name in settings.mcp_servers:
        server_config = settings.mcp_servers[server_name]
        global_headers = dict(server_config.headers) if server_config.headers else {}

    # 用户级 headers（覆盖全局同名 key）
    user_headers = load_user_mcp_auth(user_id, server_name)

    # 合并：用户级优先
    merged = {**global_headers, **user_headers}
    return merged


def _extract_server_name(tool_name: str) -> str:
    """从 MCP 工具名提取 server_name。

    格式: mcp__{server}__{method} → server
    例如: mcp__email__send → email
          mcp__pdf__convert → pdf
    """
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return parts[1]
    return tool_name
