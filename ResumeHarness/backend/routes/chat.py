"""SSE 流式对话端点。"""

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from resume_agent.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    ErrorEvent,
    StatusEvent,
    StreamEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)

from resume_agent.config.settings import get_settings
from resume_agent.models.api_schemas import ChatRequest, ErrorResponse
from resume_agent.models.sse_events import (
    SseAssistantTurnComplete,
    SseError,
    SsePing,
    SseStatus,
    SseTextDelta,
    SseToolExecutionCompleted,
    SseToolExecutionStarted,
    format_sse_data,
)
from resume_agent.runtime import RuntimeBundle
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_session_pool(request: Request) -> ResumeSessionPool:
    """从 app state 获取会话池。"""
    from backend.app import session_pool
    if session_pool is None:
        raise RuntimeError("会话池未初始化")
    return session_pool


def _stream_event_to_sse(event: StreamEvent) -> str | None:
    """将 StreamEvent 转换为 SSE 数据行。"""
    if isinstance(event, AssistantTextDelta):
        return format_sse_data(SseTextDelta(text=event.text))
    elif isinstance(event, ToolExecutionStarted):
        return format_sse_data(SseToolExecutionStarted(
            tool_name=event.tool_name,
            tool_input=event.tool_input,
        ))
    elif isinstance(event, ToolExecutionCompleted):
        return format_sse_data(SseToolExecutionCompleted(
            tool_name=event.tool_name,
            output=event.output,
            is_error=event.is_error,
        ))
    elif isinstance(event, StatusEvent):
        return format_sse_data(SseStatus(message=event.message))
    elif isinstance(event, ErrorEvent):
        return format_sse_data(SseError(
            code=2001,
            message=event.message,
        ))
    elif isinstance(event, AssistantTurnComplete):
        usage_data = None
        if event.usage:
            usage_data = {
                "input_tokens": event.usage.input_tokens,
                "output_tokens": event.usage.output_tokens,
            }
        return format_sse_data(SseAssistantTurnComplete(usage=usage_data))
    # CompactProgressEvent 等暂不处理
    return None


async def _chat_stream(
    bundle: RuntimeBundle,
    prompt: str,
) -> AsyncIterator[str]:
    """生成 SSE 流式事件。"""
    try:
        async for event in bundle.engine.submit_message(prompt):
            sse_data = _stream_event_to_sse(event)
            if sse_data:
                yield sse_data
    except Exception as exc:
        logger.error("对话流式处理异常: %s", exc, exc_info=True)
        yield format_sse_data(SseError(code=2001, message=f"对话处理失败: {exc}"))
        yield format_sse_data(SseAssistantTurnComplete())


@router.post("/chat")
async def chat(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """SSE 流式对话端点。

    P0/P1 开发模式下不要求认证，使用默认 user_id dev_user。
    """
    settings = get_settings()
    user_id = settings.effective_default_user_id

    pool = _get_session_pool(http_request)
    session_id = request.session_id or uuid.uuid4().hex[:12]

    try:
        bundle = await pool.get_or_create(
            user_id=user_id,
            session_id=session_id,
            channel="web",
        )
    except Exception as exc:
        logger.error("创建会话失败: %s", exc)
        return StreamingResponse(
            iter([format_sse_data(SseError(code=2001, message=f"创建会话失败: {exc}"))]),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _chat_stream(bundle, request.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 禁用缓冲
        },
    )
