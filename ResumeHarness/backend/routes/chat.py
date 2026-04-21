"""SSE 流式对话端点。"""

from __future__ import annotations

import json
import logging
import re
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
    SseResumeGenerated,
    SseStatus,
    SseTextDelta,
    SseToolExecutionCompleted,
    SseToolExecutionStarted,
    format_sse_data,
)
from resume_agent.resume_renderer import save_resume_snapshot
from resume_agent.runtime import RuntimeBundle
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

router = APIRouter()

# 简历内容检测正则：Markdown 中以 # 开头且包含简历相关关键词的结构
_RESUME_PATTERN = re.compile(
    r"^#\s+.+\n.*(?:工作经历|教育背景|技能|项目经历|个人简介|Professional Summary|Work Experience|Education|Skills)",
    re.MULTILINE | re.DOTALL,
)


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


def _extract_resume_content(message) -> str | None:
    """从 assistant 消息中提取简历 Markdown 内容。

    检测消息文本中是否包含简历结构（以 # 开头且包含简历关键章节）。
    如果匹配，返回完整文本；否则返回 None。
    """
    text = message.text if hasattr(message, "text") else ""
    if not text or len(text) < 100:
        return None
    if _RESUME_PATTERN.search(text):
        return text
    return None


async def _chat_stream(
    bundle: RuntimeBundle,
    prompt: str,
    user_id: str,
) -> AsyncIterator[str]:
    """生成 SSE 流式事件，附带心跳保活。"""
    import asyncio

    ping_interval = 15  # 每 15 秒发送一次心跳
    last_ping = asyncio.get_event_loop().time()

    try:
        async for event in bundle.engine.submit_message(prompt):
            sse_data = _stream_event_to_sse(event)
            if sse_data:
                yield sse_data

            # 心跳保活：检查是否需要发送 ping
            now = asyncio.get_event_loop().time()
            if now - last_ping >= ping_interval:
                yield format_sse_data(SsePing())
                last_ping = now

            # 当本轮对话完成时，检测是否有简历输出
            if isinstance(event, AssistantTurnComplete) and event.message:
                resume_md = _extract_resume_content(event.message)
                if resume_md:
                    try:
                        resume_id = save_resume_snapshot(user_id, resume_md)
                        logger.info("自动保存简历快照: user=%s resume_id=%s", user_id, resume_id)
                        yield format_sse_data(SseResumeGenerated(resume_id=resume_id))
                    except Exception as exc:
                        logger.warning("保存简历快照失败: %s", exc)

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
        _chat_stream(bundle, request.prompt, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 禁用缓冲
        },
    )
