"""SSE 流式对话端点。"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from resume_agent.api.errors import RateLimitFailure
from resume_agent.engine.stream_events import (
    ApiRetryEvent,
    AssistantTextDelta,
    AssistantTurnComplete,
    ErrorEvent,
    StatusEvent,
    StreamEvent,
    ThinkingDelta,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)
from resume_agent.exceptions import RateLimitError

from resume_agent.models.api_schemas import ChatRequest
from resume_agent.models.sse_events import (
    SseAssistantTurnComplete,
    SseError,
    SsePing,
    SseResumeData,
    SseResumeGenerated,
    SseSessionStarted,
    SseStatus,
    SseTextDelta,
    SseThinkingDelta,
    SseToolExecutionCompleted,
    SseToolExecutionStarted,
    format_sse_data,
)
from resume_agent.resume_renderer import (
    get_template_hint,
    parse_resume_data_from_markdown,
    save_resume_snapshot,
)
from resume_agent.runtime import RuntimeBundle
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 简历标记分隔相关常量
# ---------------------------------------------------------------------------

# 简历正文标记（HTML 注释风格，对 Markdown 渲染无影响）
_RESUME_MARKER_OPEN = "<!--RESUME-->"
_RESUME_MARKER_CLOSE = "<!--/RESUME-->"

# 标记的正则匹配（主路径提取用）
_RESUME_MARKER_PATTERN = re.compile(
    r"<!--RESUME-->(.*?)<!--/RESUME-->",
    re.DOTALL,
)

# 提取标记外建议内容的正则（标记之后的所有内容）
_SUGGESTIONS_AFTER_MARKER = re.compile(
    r"<!--/RESUME-->\s*(.*)",
    re.DOTALL,
)

# 提取标记前的前缀内容的正则（标记之前的所有内容）
_RESUME_PREFIX_BEFORE_MARKER = re.compile(
    r"(.*?)<!--RESUME-->",
    re.DOTALL,
)

# 简历二级章节标题（用于白名单降级路径定位简历内容区域）
_RESUME_SECTION_PATTERN = re.compile(
    r"^##\s+(?:个人简介|工作经历|教育背景|技能标签?|项目经历|Professional Summary|Work Experience|Education|Skills)",
    re.MULTILINE,
)

# 简历顶级标题（姓名行，以单个 # 开头，非 ##）
_RESUME_TITLE_PATTERN = re.compile(
    r"^#\s+[^#\n]+",
    re.MULTILINE,
)

# 白名单：已知有效的简历章节标题关键词（中英文）
_RESUME_VALID_SECTIONS = {
    "个人简介", "个人总结", "自我介绍", "简介", "总结",
    "工作经历", "工作经验", "职业经历",
    "教育背景", "教育经历", "学历",
    "专业技能", "技能", "核心技能", "技术栈", "技能标签",
    "项目经历", "项目经验", "核心项目",
    "profile", "summary", "about",
    "experience", "work experience", "employment",
    "education", "academic",
    "skills", "technical skills", "competencies",
    "projects", "project experience",
}


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

    双路径策略：
    1. 标记提取（主路径）：LLM 使用 <!--RESUME--> / <!--/RESUME--> 标记时，直接提取标记间内容
    2. 白名单过滤（降级路径）：LLM 未使用标记时，只保留已知简历章节，丢弃非简历章节
    """
    text = message.text if hasattr(message, "text") else ""
    if not text or len(text) < 100:
        return None

    # ---- 主路径：标记提取 ----
    marker_match = _RESUME_MARKER_PATTERN.search(text)
    if marker_match:
        resume_text = marker_match.group(1).strip()
        if len(resume_text) >= 50:
            logger.debug("简历提取: 使用标记分隔路径")
            return resume_text

    # ---- 降级路径：白名单过滤 ----
    logger.debug("简历提取: 未找到标记，使用白名单过滤路径")

    # 第一步：找到简历特征章节
    section_match = _RESUME_SECTION_PATTERN.search(text)
    if not section_match:
        return None

    # 第二步：从该章节位置往前找 # 级标题（姓名行）
    search_before = text[:section_match.start()]
    title_matches = list(_RESUME_TITLE_PATTERN.finditer(search_before))
    if title_matches:
        start_pos = title_matches[-1].start()
    else:
        start_pos = section_match.start()

    resume_text = text[start_pos:]

    # 第三步：白名单过滤——只保留已知简历章节及其内容
    lines = resume_text.split("\n")
    filtered_lines: list[str] = []
    in_valid_section = True  # 头部（姓名+联系方式）始终有效

    for line in lines:
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            section_title = h2_match.group(1).strip()
            # 检查是否是已知简历章节
            if section_title.lower() in {s.lower() for s in _RESUME_VALID_SECTIONS}:
                in_valid_section = True
                filtered_lines.append(line)
            else:
                in_valid_section = False
            continue

        if in_valid_section:
            filtered_lines.append(line)

    result = "\n".join(filtered_lines).strip()
    return result if len(result) >= 100 else None


def _extract_suggestions(message) -> str:
    """从 assistant 消息中提取标记外的建议内容。

    提取 <!--/RESUME--> 标记之后的所有文本，作为优化建议返回给前端展示。
    """
    text = message.text if hasattr(message, "text") else ""
    if not text:
        return ""

    # 主路径：从标记后提取
    marker_match = _SUGGESTIONS_AFTER_MARKER.search(text)
    if marker_match:
        suggestions = marker_match.group(1).strip()
        return suggestions

    # 降级路径：从白名单过滤时被丢弃的非简历章节中提取
    # 找到第一个非简历章节及其后续内容
    section_match = _RESUME_SECTION_PATTERN.search(text)
    if not section_match:
        return ""

    search_before = text[:section_match.start()]
    title_matches = list(_RESUME_TITLE_PATTERN.finditer(search_before))
    start_pos = title_matches[-1].start() if title_matches else section_match.start()

    resume_text = text[start_pos:]
    lines = resume_text.split("\n")
    suggestion_lines: list[str] = []
    in_valid_section = True

    for line in lines:
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            section_title = h2_match.group(1).strip()
            if section_title.lower() in {s.lower() for s in _RESUME_VALID_SECTIONS}:
                in_valid_section = True
            else:
                in_valid_section = False
                suggestion_lines.append(line)  # 非简历章节标题
            continue
        if not in_valid_section:
            suggestion_lines.append(line)

    result = "\n".join(suggestion_lines).strip()
    return result


def _extract_resume_prefix(message) -> str:
    """从 assistant 消息中提取标记前的前缀内容。

    提取 <!--RESUME--> 标记之前的所有文本，通常是 LLM 的引导语。
    """
    text = message.text if hasattr(message, "text") else ""
    if not text:
        return ""

    # 主路径：从标记前提取
    marker_match = _RESUME_PREFIX_BEFORE_MARKER.search(text)
    if marker_match:
        prefix = marker_match.group(1).strip()
        return prefix

    # 降级路径：白名单过滤时，简历开始之前的文本
    section_match = _RESUME_SECTION_PATTERN.search(text)
    if not section_match:
        return ""

    search_before = text[:section_match.start()]
    title_matches = list(_RESUME_TITLE_PATTERN.finditer(search_before))
    if title_matches:
        prefix = text[:title_matches[-1].start()].strip()
        return prefix

    return ""


class _StreamingMarkerFilter:
    """流式文本中过滤 <!--RESUME--> / <!--/RESUME--> 标记。

    标记可能被拆分到多个 text_delta 块中，需要缓冲检测。
    """

    _MAX_MARKER_LEN = len(_RESUME_MARKER_CLOSE)  # 15

    def __init__(self) -> None:
        self._tail = ""

    def feed(self, text: str) -> str:
        """输入流式文本，返回过滤后的文本。"""
        combined = self._tail + text

        # 替换完整标记
        combined = combined.replace(_RESUME_MARKER_OPEN, "")
        combined = combined.replace(_RESUME_MARKER_CLOSE, "")

        # 检查尾部是否可能是标记的前缀（被拆分的情况）
        safe_end = len(combined)
        for i in range(1, min(self._MAX_MARKER_LEN, len(combined)) + 1):
            tail_candidate = combined[-i:]
            if _RESUME_MARKER_OPEN.startswith(tail_candidate) or _RESUME_MARKER_CLOSE.startswith(tail_candidate):
                safe_end = len(combined) - i
                break

        self._tail = combined[safe_end:]
        return combined[:safe_end]

    def flush(self) -> str:
        """刷新缓冲区，返回剩余文本。"""
        remaining = self._tail
        self._tail = ""
        return remaining


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
    marker_filter = _StreamingMarkerFilter()

    try:
        async for event in bundle.engine.submit_message(prompt):
            # 对 text_delta 事件过滤标记标签
            if isinstance(event, AssistantTextDelta):
                filtered_text = marker_filter.feed(event.text)
                if filtered_text:
                    yield format_sse_data(SseTextDelta(text=filtered_text))
            else:
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
                # 刷新标记过滤器
                remaining = marker_filter.flush()
                if remaining:
                    yield format_sse_data(SseTextDelta(text=remaining))

                resume_md = _extract_resume_content(event.message)
                if resume_md:
                    try:
                        resume_id = save_resume_snapshot(user_id, resume_md)
                        logger.info("自动保存简历快照: user=%s resume_id=%s", user_id, resume_id)
                        yield format_sse_data(SseResumeGenerated(resume_id=resume_id))

                        # 解析并推送结构化数据，前端自动升级为组件渲染
                        resume_data_dict = parse_resume_data_from_markdown(resume_md)
                        if resume_data_dict:
                            # 提取标记外的建议内容
                            suggestions = _extract_suggestions(event.message)
                            # 提取标记前的前缀内容
                            resume_prefix = _extract_resume_prefix(event.message)
                            # 根据简历内容智能推荐模板
                            template_hint = get_template_hint(jd_text=resume_md)
                            yield format_sse_data(SseResumeData(
                                resume_id=resume_id,
                                data=resume_data_dict,
                                template_hint=template_hint,
                                suggestions=suggestions,
                                resume_prefix=resume_prefix,
                            ))
                    except Exception as exc:
                        logger.warning("保存简历快照失败: %s", exc)

    except RateLimitFailure as exc:
        logger.warning("DeepSeek 速率限制: %s", exc)
        yield format_sse_data(SseStatus(message="AI 服务繁忙，正在排队重试..."))
        yield format_sse_data(SseError(
            code=2002,
            message="AI 服务当前请求过多，请稍等片刻后重新发送",
        ))
        yield format_sse_data(SseAssistantTurnComplete())
    except RateLimitError as exc:
        logger.warning("速率限制: %s", exc)
        yield format_sse_data(SseError(
            code=2002,
            message=str(exc.message) if hasattr(exc, "message") else str(exc),
        ))
        yield format_sse_data(SseAssistantTurnComplete())
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
            latest_user_prompt=request.prompt,
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
