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
    ThinkingDelta,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)

from resume_agent.models.api_schemas import ChatRequest
from resume_agent.models.sse_events import (
    SseAssistantTurnComplete,
    SseError,
    SsePing,
    SseResumeGenerated,
    SseSessionStarted,
    SseStatus,
    SseTextDelta,
    SseThinkingDelta,
    SseToolExecutionCompleted,
    SseToolExecutionStarted,
    format_sse_data,
)
from resume_agent.resume_renderer import save_resume_snapshot
from resume_agent.runtime import RuntimeBundle
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

router = APIRouter()

# 简历二级章节标题（用于定位简历内容区域）
_RESUME_SECTION_PATTERN = re.compile(
    r"^##\s+(?:个人简介|工作经历|教育背景|技能标签?|项目经历|Professional Summary|Work Experience|Education|Skills)",
    re.MULTILINE,
)

# 简历顶级标题（姓名行，以单个 # 开头，非 ##）
_RESUME_TITLE_PATTERN = re.compile(
    r"^#\s+[^#\n]+",
    re.MULTILINE,
)

# 简历后面的非简历章节标题（优化说明、修改建议等）
_NON_RESUME_HEADING = re.compile(
    r"^#{1,3}\s+(?:优化说明|修改建议|改动说明|修改详情|调整说明|优化详情|优化建议|Optimization Notes|Changes|Summary of Changes)",
    re.MULTILINE,
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
    elif isinstance(event, ThinkingDelta):
        return format_sse_data(SseThinkingDelta(text=event.text))
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

    策略：
    1. 搜索简历特征二级章节（## 个人简介 / ## 工作经历 / ...）
    2. 从该章节往前找最近的 # 级标题（简历姓名行）作为起点
    3. 从起点截取到末尾
    4. 截断非简历章节（## 优化说明 等）
    """
    text = message.text if hasattr(message, "text") else ""
    if not text or len(text) < 100:
        return None

    # 第一步：找到简历特征章节
    section_match = _RESUME_SECTION_PATTERN.search(text)
    if not section_match:
        return None

    # 第二步：从该章节位置往前找 # 级标题（姓名行）
    search_before = text[:section_match.start()]
    title_matches = list(_RESUME_TITLE_PATTERN.finditer(search_before))
    if title_matches:
        # 取最后一个（最靠近章节的）# 标题
        start_pos = title_matches[-1].start()
    else:
        # 没找到 # 标题，从章节本身开始
        start_pos = section_match.start()

    resume_text = text[start_pos:]

    # 第三步：截断简历后面的非简历章节
    non_resume = _NON_RESUME_HEADING.search(resume_text)
    if non_resume and non_resume.start() > 0:
        resume_text = resume_text[:non_resume.start()]

    return resume_text.rstrip()


async def _chat_stream(
    bundle: RuntimeBundle,
    prompt: str,
    user_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """生成 SSE 流式事件，附带心跳保活。"""
    import asyncio

    # 首先发送 session_id
    yield format_sse_data(SseSessionStarted(session_id=session_id))

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
    """SSE 流式对话端点。需要 JWT 认证。"""
    user_id = http_request.state.user_id

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
        _chat_stream(bundle, request.prompt, user_id=user_id, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 禁用缓冲
        },
    )
