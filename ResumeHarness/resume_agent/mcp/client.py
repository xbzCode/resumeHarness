"""MCP HTTP 客户端。

连接单个 HTTP MCP 服务器，发现工具、调用工具。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from resume_agent.config.settings import McpServerConfig
from resume_agent.exceptions import McpUnavailableError

log = logging.getLogger(__name__)

# MCP HTTP 请求超时
_MCP_TIMEOUT = 30.0
# MCP 工具调用超时（PDF 渲染等可能较慢）
_MCP_CALL_TIMEOUT = 120.0


class McpToolInfo(BaseModel):
    """MCP 工具元信息。"""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpCallResult(BaseModel):
    """MCP 工具调用结果。"""

    content: Any = None
    is_error: bool = False
    error_message: str = ""


class McpHttpClient:
    """单个 HTTP MCP 服务器的客户端。

    遵循 MCP HTTP 协议：
    - POST /tools/list  → 发现工具
    - POST /tools/call  → 调用工具
    - GET  /health      → 健康检查
    """

    def __init__(self, server_name: str, config: McpServerConfig) -> None:
        self._name = server_name
        self._url = config.url.rstrip("/")
        self._default_headers: dict[str, str] = dict(config.headers) if config.headers else {}
        self._tools: list[McpToolInfo] = []
        self._connected = False
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """服务器名称。"""
        return self._name

    @property
    def url(self) -> str:
        """服务器 URL。"""
        return self._url

    @property
    def tools(self) -> list[McpToolInfo]:
        """已发现的工具列表。"""
        return list(self._tools)

    @property
    def is_connected(self) -> bool:
        """是否已连接。"""
        return self._connected

    def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 httpx 客户端（连接复用）。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._url,
                headers=self._default_headers,
                timeout=httpx.Timeout(_MCP_TIMEOUT),
            )
        return self._client

    async def connect(self) -> None:
        """连接 MCP 服务器并发现工具。"""
        if not self._url:
            log.warning("MCP 服务器 %s 未配置 URL，跳过连接", self._name)
            return

        try:
            # 健康检查
            client = self._get_client()
            resp = await client.get("/health")
            if resp.status_code != 200:
                log.warning("MCP 服务器 %s 健康检查失败: HTTP %d", self._name, resp.status_code)
                return

            # 发现工具
            await self.discover_tools()
            self._connected = True
            log.info(
                "MCP 服务器 %s 连接成功，发现 %d 个工具",
                self._name,
                len(self._tools),
            )
        except httpx.ConnectError as exc:
            log.warning("MCP 服务器 %s 连接失败: %s", self._name, exc)
        except Exception as exc:
            log.warning("MCP 服务器 %s 连接异常: %s", self._name, exc)

    async def disconnect(self) -> None:
        """断开连接，释放资源。"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        self._connected = False
        self._tools = []
        log.info("MCP 服务器 %s 已断开", self._name)

    async def discover_tools(self) -> list[McpToolInfo]:
        """发现 MCP 服务器上的可用工具。

        Returns:
            工具信息列表
        """
        try:
            client = self._get_client()
            resp = await client.post("/tools/list")
            resp.raise_for_status()
            data = resp.json()

            # 解析工具列表
            tools_data = data.get("tools", [])
            self._tools = []
            for tool_data in tools_data:
                tool_info = McpToolInfo(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", tool_data.get("input_schema", {})),
                )
                if tool_info.name:
                    self._tools.append(tool_info)

            return list(self._tools)
        except Exception as exc:
            log.warning("MCP 服务器 %s 工具发现失败: %s", self._name, exc)
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        extra_headers: dict[str, str] | None = None,
    ) -> McpCallResult:
        """调用 MCP 工具。

        Args:
            tool_name: 工具名称（不含 mcp__ 前缀）
            arguments: 工具参数
            extra_headers: 额外的请求头（如用户级认证）

        Returns:
            调用结果
        """
        try:
            client = self._get_client()

            # 合并额外 headers
            headers: dict[str, str] = {}
            if extra_headers:
                headers.update(extra_headers)

            # 设置较长的调用超时
            request_timeout = httpx.Timeout(_MCP_CALL_TIMEOUT)

            resp = await client.post(
                "/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments,
                },
                headers=headers or None,
                timeout=request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # 解析结果
            is_error = data.get("isError", data.get("is_error", False))
            content = data.get("content", "")
            error_message = data.get("errorMessage", data.get("error_message", ""))

            # 如果 content 是列表（MCP 标准格式），提取文本
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = "\n".join(text_parts) if text_parts else str(content)

            return McpCallResult(
                content=content,
                is_error=is_error,
                error_message=error_message,
            )
        except httpx.ConnectError:
            raise McpUnavailableError(f"MCP 服务器 {self._name} 连接失败，请检查服务是否启动")
        except httpx.TimeoutException:
            raise McpUnavailableError(f"MCP 服务器 {self._name} 调用超时")
        except McpUnavailableError:
            raise
        except Exception as exc:
            return McpCallResult(
                content=str(exc),
                is_error=True,
                error_message=str(exc),
            )

    async def health_check(self) -> bool:
        """检查 MCP 服务器健康状态。"""
        try:
            client = self._get_client()
            resp = await client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
