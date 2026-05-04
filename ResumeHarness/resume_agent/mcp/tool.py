"""MCP 工具包装器。

将远程 MCP 工具注册为 BaseTool，支持用户级认证注入。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, create_model

from resume_agent.mcp.client import McpHttpClient, McpToolInfo
from resume_agent.mcp_auth import get_mcp_headers
from resume_agent.tools.base import BaseTool, ToolExecutionContext, ToolResult

log = logging.getLogger(__name__)


def _create_input_model(tool_info: McpToolInfo) -> type[BaseModel]:
    """根据 MCP 工具的 input_schema 动态创建 Pydantic 模型。

    Args:
        tool_info: MCP 工具元信息

    Returns:
        动态创建的 Pydantic 模型类
    """
    schema = tool_info.input_schema
    if not schema:
        # 无参数的工具
        return create_model(
            f"{tool_info.name}_input",
        )

    # 从 JSON Schema 的 properties 创建 Pydantic 字段
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    field_definitions: dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        description = prop_schema.get("description", "")
        default = ... if prop_name in required_fields else None

        # 类型映射：JSON Schema → Python
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(prop_type, str)

        if default is None:
            field_definitions[prop_name] = (
                python_type,
                Field(default=None, description=description),
            )
        else:
            field_definitions[prop_name] = (
                python_type,
                Field(description=description),
            )

    model_name = f"{tool_info.name}_input"
    return create_model(model_name, **field_definitions)


class McpToolWrapper(BaseTool):
    """MCP 工具的 BaseTool 包装器。

    将远程 MCP 工具注册到 ToolRegistry，支持：
    - 工具发现和注册
    - 工具调用（通过 HTTP MCP 协议）
    - 用户级认证 headers 注入（通过 mcp_auth.py）
    """

    def __init__(
        self,
        server_name: str,
        tool_info: McpToolInfo,
        client: McpHttpClient,
    ) -> None:
        self._server_name = server_name
        self._tool_info = tool_info
        self._client = client

        # 设置 BaseTool 属性
        self.name = f"mcp__{server_name}__{tool_info.name}"
        self.description = tool_info.description or f"MCP 工具: {tool_info.name}"
        self.input_model = _create_input_model(tool_info)
        self.category = tool_info.annotations.category or "MCP代理"
        self.is_read_only_default = tool_info.annotations.read_only_hint

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        """执行 MCP 工具调用。

        自动注入用户级认证 headers。
        """
        # 获取用户 ID
        user_id = context.metadata.get("user_id", "")

        # 获取合并后的认证 headers
        extra_headers: dict[str, str] = {}
        if user_id:
            try:
                extra_headers = await get_mcp_headers(self.name, user_id)
            except Exception as exc:
                log.warning("获取 MCP 认证失败 tool=%s user=%s: %s", self.name, user_id, exc)

        # 序列化参数
        arguments_dict = arguments.model_dump(exclude_none=True)

        # 调用远程 MCP 工具
        try:
            result = await self._client.call_tool(
                tool_name=self._tool_info.name,
                arguments=arguments_dict,
                extra_headers=extra_headers if extra_headers else None,
            )

            if result.is_error:
                return ToolResult(
                    output=result.error_message or str(result.content) or "MCP 工具调用失败",
                    is_error=True,
                )

            # 格式化输出
            content = result.content
            if isinstance(content, (dict, list)):
                output = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                output = str(content) if content else ""

            return ToolResult(output=output)

        except Exception as exc:
            log.error("MCP 工具调用异常 tool=%s: %s", self.name, exc)
            return ToolResult(
                output=f"MCP 工具调用失败: {exc}",
                is_error=True,
            )

    def is_read_only(self, arguments: BaseModel) -> bool:
        """判断工具是否只读。

        优先从 MCP ToolSpec 的 annotations.readOnlyHint 读取。
        未声明 annotations 时默认 false（安全降级）。
        """
        return self._tool_info.annotations.read_only_hint

    def to_api_schema(self) -> dict[str, Any]:
        """返回工具的 API Schema。"""
        schema = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }
        return schema
