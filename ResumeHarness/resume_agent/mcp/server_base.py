"""MCP 服务器共享框架。

提供 McpServerBase 基类，第三方只需实现工具逻辑，
即可快速搭建符合 MCP 协议的 HTTP 服务器。

使用示例::

    from resume_agent.mcp.server_base import McpServerBase

    class MyServer(McpServerBase):
        server_name = "my-server"
        server_version = "1.0.0"

        def setup_tools(self):
            self.register_tool(
                name="my_tool",
                description="我的自定义工具",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "查询内容"},
                    },
                    "required": ["query"],
                },
                handler=self._handle_my_tool,
                annotations={"readOnlyHint": True, "category": "自定义"},
            )

        async def _handle_my_tool(self, arguments: dict) -> str:
            return f"处理结果: {arguments['query']}"

    if __name__ == "__main__":
        MyServer().run()
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Awaitable

log = logging.getLogger(__name__)


class McpServerBase:
    """MCP 服务器基类，自动实现协议端点。

    子类只需：
    1. 设置 server_name 和 server_version
    2. 在 setup_tools() 中调用 register_tool() 注册工具
    3. 实现对应的 handler 函数
    """

    server_name: str = ""
    server_version: str = "1.0.0"

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[[dict], Awaitable[str]]] = {}
        self.setup_tools()

    def setup_tools(self) -> None:
        """子类重写此方法注册工具。"""
        pass

    def register_tool(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[[dict], Awaitable[str]],
        annotations: dict[str, Any] | None = None,
    ) -> None:
        """注册一个 MCP 工具。

        Args:
            name: 工具名称（唯一标识符）
            description: 工具描述
            input_schema: JSON Schema 格式的输入定义
            handler: 异步处理函数，接收 arguments dict，返回结果字符串
            annotations: 工具注解（readOnlyHint/destructiveHint 等）
        """
        if name in self._tools:
            log.warning("工具 %s 重复注册，覆盖旧定义", name)

        tool_spec: dict[str, Any] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }

        # 添加 annotations
        if annotations:
            # 确保必需字段存在
            ann = dict(annotations)
            if "readOnlyHint" not in ann:
                ann["readOnlyHint"] = False
            if "destructiveHint" not in ann:
                ann["destructiveHint"] = False
            tool_spec["annotations"] = ann
        else:
            # 默认 annotations：非只读、非破坏性
            tool_spec["annotations"] = {
                "readOnlyHint": False,
                "destructiveHint": False,
            }

        self._tools[name] = tool_spec
        self._handlers[name] = handler
        log.info("注册 MCP 工具: %s", name)

    def create_app(self) -> Any:
        """创建 FastAPI 应用实例。"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        app = FastAPI(
            title=f"MCP Server: {self.server_name}",
            version=self.server_version,
        )

        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {
                "status": "ok",
                "version": self.server_version,
                "server": self.server_name,
            }

        @app.post("/tools/list")
        async def tools_list() -> dict[str, Any]:
            return {"tools": list(self._tools.values())}

        @app.post("/tools/call")
        async def tools_call(request: Request) -> JSONResponse:
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={"isError": True, "errorMessage": "请求体不是有效的 JSON"},
                )

            tool_name = body.get("name", "")
            arguments = body.get("arguments", {})

            if tool_name not in self._handlers:
                return JSONResponse(
                    status_code=404,
                    content={
                        "isError": True,
                        "errorMessage": f"工具不存在: {tool_name}",
                    },
                )

            handler = self._handlers[tool_name]
            try:
                result = await handler(arguments)
                return JSONResponse(
                    content={
                        "content": [{"type": "text", "text": result}],
                        "isError": False,
                    }
                )
            except Exception as exc:
                log.error("工具 %s 执行失败: %s", tool_name, exc)
                return JSONResponse(
                    status_code=500,
                    content={
                        "isError": True,
                        "errorMessage": str(exc),
                    },
                )

        return app

    def run(self, host: str = "0.0.0.0", port: int = 9100) -> None:
        """启动 MCP 服务器。"""
        import uvicorn

        app = self.create_app()
        log.info("启动 MCP 服务器 %s v%s on %s:%d", self.server_name, self.server_version, host, port)
        uvicorn.run(app, host=host, port=port)
