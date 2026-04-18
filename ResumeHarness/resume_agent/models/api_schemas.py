"""请求/响应 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """SSE 对话请求。"""

    prompt: str = Field(description="用户输入的提示词")
    session_id: str | None = Field(default=None, description="续接已有会话 ID")


class ChatResponse(BaseModel):
    """对话响应元数据。"""

    session_id: str
    user_id: str
    model: str


class ErrorResponse(BaseModel):
    """错误响应。"""

    code: int
    message: str
