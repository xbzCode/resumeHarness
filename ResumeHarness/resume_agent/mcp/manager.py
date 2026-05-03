"""MCP 客户端管理器（进程级单例）。

管理所有 HTTP MCP 连接，发现工具并注册到 ToolRegistry。
"""

from __future__ import annotations

import logging
from typing import Any

from resume_agent.config.settings import McpServerConfig, get_settings
from resume_agent.mcp.client import McpHttpClient, McpToolInfo
from resume_agent.mcp.tool import McpToolWrapper
from resume_agent.tools.base import ToolRegistry

log = logging.getLogger(__name__)


class McpClientManager:
    """进程级 MCP 客户端管理器。

    职责：
    1. 管理所有 HTTP MCP 连接
    2. 发现远程 MCP 工具
    3. 将 MCP 工具注册到 ToolRegistry
    4. 提供连接状态信息
    """

    def __init__(self, mcp_servers: dict[str, McpServerConfig] | None = None) -> None:
        self._servers = mcp_servers or {}
        self._clients: dict[str, McpHttpClient] = {}
        self._initialized = False

    @property
    def clients(self) -> dict[str, McpHttpClient]:
        """获取所有 MCP 客户端。"""
        return dict(self._clients)

    @property
    def is_initialized(self) -> bool:
        """是否已初始化。"""
        return self._initialized

    async def initialize(self) -> None:
        """初始化所有 MCP 连接。

        遍历配置中的 MCP 服务器，逐一连接并发现工具。
        连接失败的服务器会被跳过，不影响其他服务器。
        """
        if self._initialized:
            return

        log.info("初始化 MCP 客户端管理器，共 %d 个服务器配置", len(self._servers))

        for server_name, config in self._servers.items():
            # 跳过未启用的服务器
            if hasattr(config, "enabled") and not config.enabled:
                log.info("MCP 服务器 %s 已禁用，跳过", server_name)
                continue

            if not config.url:
                log.info("MCP 服务器 %s 未配置 URL，跳过", server_name)
                continue

            client = McpHttpClient(server_name, config)
            self._clients[server_name] = client

            try:
                await client.connect()
            except Exception as exc:
                log.warning("MCP 服务器 %s 连接失败: %s", server_name, exc)

        self._initialized = True
        connected = sum(1 for c in self._clients.values() if c.is_connected)
        log.info("MCP 客户端管理器初始化完成: %d/%d 服务器已连接", connected, len(self._clients))

    async def shutdown(self) -> None:
        """关闭所有 MCP 连接，释放资源。"""
        for client in self._clients.values():
            try:
                await client.disconnect()
            except Exception as exc:
                log.warning("MCP 服务器 %s 断开连接异常: %s", client.name, exc)
        self._clients.clear()
        self._initialized = False
        log.info("MCP 客户端管理器已关闭")

    def register_tools_to_registry(self, tool_registry: ToolRegistry) -> int:
        """将已发现的 MCP 工具注册到 ToolRegistry。

        Args:
            tool_registry: 工具注册表

        Returns:
            注册的工具数量
        """
        registered_count = 0

        for server_name, client in self._clients.items():
            if not client.is_connected:
                continue

            for tool_info in client.tools:
                wrapper = McpToolWrapper(
                    server_name=server_name,
                    tool_info=tool_info,
                    client=client,
                )
                try:
                    tool_registry.register(wrapper)
                    registered_count += 1
                    log.info(
                        "注册 MCP 工具: %s (from %s)",
                        wrapper.name,
                        server_name,
                    )
                except Exception as exc:
                    log.warning(
                        "注册 MCP 工具失败: %s (from %s): %s",
                        wrapper.name,
                        server_name,
                        exc,
                    )

        return registered_count

    def unregister_tools_from_registry(self, tool_registry: ToolRegistry) -> int:
        """从 ToolRegistry 中移除所有 MCP 工具。

        Args:
            tool_registry: 工具注册表

        Returns:
            移除的工具数量
        """
        removed_count = 0
        mcp_tools = [
            tool for tool in tool_registry.list_tools()
            if tool.name.startswith("mcp__")
        ]

        for tool in mcp_tools:
            tool_registry.unregister(tool.name)
            removed_count += 1

        return removed_count

    async def refresh_tools(self, tool_registry: ToolRegistry) -> int:
        """刷新 MCP 工具列表（重新发现并注册）。

        先移除旧的 MCP 工具，再重新连接发现并注册。

        Args:
            tool_registry: 工具注册表

        Returns:
            新注册的工具数量
        """
        # 移除旧的 MCP 工具
        self.unregister_tools_from_registry(tool_registry)

        # 重新连接发现工具
        for client in self._clients.values():
            try:
                await client.discover_tools()
            except Exception as exc:
                log.warning("MCP 服务器 %s 工具刷新失败: %s", client.name, exc)

        # 重新注册
        return self.register_tools_to_registry(tool_registry)

    def get_status(self) -> dict[str, Any]:
        """获取所有 MCP 服务器的连接状态。

        Returns:
            状态信息字典
        """
        servers: dict[str, Any] = {}
        for server_name, client in self._clients.items():
            servers[server_name] = {
                "url": client.url,
                "connected": client.is_connected,
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    for tool in client.tools
                ],
            }

        # 未连接的已配置服务器
        for server_name, config in self._servers.items():
            if server_name not in self._clients:
                servers[server_name] = {
                    "url": config.url,
                    "connected": False,
                    "tools": [],
                    "reason": "未配置 URL" if not config.url else "连接失败",
                }

        return {
            "initialized": self._initialized,
            "total_servers": len(self._servers),
            "connected_servers": sum(1 for c in self._clients.values() if c.is_connected),
            "servers": servers,
        }


# ---------------------------------------------------------------------------
# 进程级单例
# ---------------------------------------------------------------------------

_shared_manager: McpClientManager | None = None


def get_mcp_manager() -> McpClientManager:
    """获取进程级 McpClientManager 单例。

    首次调用时从 settings 加载配置创建实例。
    注意：需要显式调用 initialize() 才会连接 MCP 服务器。
    """
    global _shared_manager
    if _shared_manager is None:
        settings = get_settings()
        _shared_manager = McpClientManager(mcp_servers=settings.mcp_servers)
    return _shared_manager


def reset_mcp_manager() -> None:
    """重置 McpClientManager 单例（主要用于测试）。"""
    global _shared_manager
    _shared_manager = None
