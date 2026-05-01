"""记忆写入工具，供 LLM 在对话中主动调用。"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from resume_agent.tools.base import BaseTool, ToolExecutionContext, ToolResult

from resume_agent.memory.manager import write_memory_file, WRITABLE_MEMORY_FILES

log = logging.getLogger(__name__)


class MemoryWriteInput(BaseModel):
    """memory_write 工具输入。"""

    doc_name: str = Field(
        description="目标记忆文件名",
    )
    content: str = Field(
        description="要追加或更新的内容（Markdown 格式）",
    )
    mode: str = Field(
        default="append",
        description="追加还是替换（偏好用 append）",
    )


class MemoryWriteTool(BaseTool):
    """记忆写入工具，供 LLM 在对话中主动调用。

    当用户在对话中明确表达了求职偏好、写作风格、技能标签等信息时，
    应主动调用此工具持久化，以便后续对话自动遵循。
    """

    name = "memory_write"
    description = (
        "将用户表达的偏好、技能、经验等信息写入用户记忆文件。"
        "当用户在对话中明确表达了求职偏好、写作风格、技能标签等信息时，"
        "应主动调用此工具持久化，以便后续对话自动遵循。"
        f"允许的文件名: {', '.join(WRITABLE_MEMORY_FILES)}"
    )
    input_model = MemoryWriteInput

    async def execute(self, arguments: MemoryWriteInput, context: ToolExecutionContext) -> ToolResult:
        """执行记忆写入。"""
        # 从 metadata 中获取 user_id（由 QueryEngine 在 tool_metadata 中注入）
        user_id = context.metadata.get("user_id")
        if not user_id:
            return ToolResult(
                output="无法确定用户身份，记忆写入失败",
                is_error=True,
            )

        if arguments.doc_name not in WRITABLE_MEMORY_FILES:
            return ToolResult(
                output=f"不支持的记忆文件名: {arguments.doc_name}。允许的文件: {', '.join(WRITABLE_MEMORY_FILES)}",
                is_error=True,
            )

        if arguments.mode not in ("append", "replace"):
            return ToolResult(
                output=f"不支持的写入模式: {arguments.mode}，请使用 'append' 或 'replace'",
                is_error=True,
            )

        try:
            path = write_memory_file(
                user_id=user_id,
                doc_name=arguments.doc_name,
                content=arguments.content,
                mode=arguments.mode,
            )
            return ToolResult(
                output=f"已成功写入记忆文件 {arguments.doc_name}（{arguments.mode} 模式），路径: {path}",
            )
        except ValueError as exc:
            return ToolResult(output=str(exc), is_error=True)
        except Exception as exc:
            log.error("写入记忆文件失败: %s", exc)
            return ToolResult(output=f"写入记忆文件失败: {exc}", is_error=True)

    def is_read_only(self, arguments: MemoryWriteInput) -> bool:
        return False
