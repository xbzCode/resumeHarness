"""SSE 事件类型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class SseTextDelta:
    """逐字文本增量。"""

    type: Literal["text_delta"] = "text_delta"
    text: str = ""


@dataclass(frozen=True)
class SseToolExecutionStarted:
    """工具开始执行通知。"""

    type: Literal["tool_execution_started"] = "tool_execution_started"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None


@dataclass(frozen=True)
class SseToolExecutionCompleted:
    """工具执行结果。"""

    type: Literal["tool_execution_completed"] = "tool_execution_completed"
    tool_name: str = ""
    output: str = ""
    is_error: bool = False


@dataclass(frozen=True)
class SseStatus:
    """系统状态消息。"""

    type: Literal["status"] = "status"
    message: str = ""


@dataclass(frozen=True)
class SseError:
    """错误事件。"""

    type: Literal["error"] = "error"
    code: int = 0
    message: str = ""


@dataclass(frozen=True)
class SseAssistantTurnComplete:
    """本轮对话完成。"""

    type: Literal["assistant_turn_complete"] = "assistant_turn_complete"
    usage: dict[str, int] | None = None


@dataclass(frozen=True)
class SsePing:
    """心跳保活。"""

    type: Literal["ping"] = "ping"


@dataclass(frozen=True)
class SseResumeGenerated:
    """简历生成完成通知。"""

    type: Literal["resume_generated"] = "resume_generated"
    resume_id: str = ""


@dataclass(frozen=True)
class SseResumeData:
    """简历结构化数据推送，前端收到后自动升级为组件渲染。"""

    type: Literal["resume_data"] = "resume_data"
    resume_id: str = ""
    data: dict[str, Any] | None = None
    template_hint: str = "professional"
    suggestions: str = ""
    resume_prefix: str = ""


@dataclass(frozen=True)
class SseThinkingDelta:
    """推理/思考过程增量。"""

    type: Literal["thinking_delta"] = "thinking_delta"
    text: str = ""


@dataclass(frozen=True)
class SseSessionStarted:
    """会话开始通知，携带 session_id。"""

    type: Literal["session_started"] = "session_started"
    session_id: str = ""


@dataclass(frozen=True)
class SseResumeScore:
    """简历评分结果推送。"""

    type: Literal["resume_score"] = "resume_score"
    resume_id: str = ""
    score: float = 0.0
    dimensions: dict[str, Any] | None = None
    suggestions: list[str] | None = None
    jd_keywords_matched: list[str] | None = None
    jd_keywords_missing: list[str] | None = None


@dataclass(frozen=True)
class SseConnectionTimeout:
    """连接超时。"""

    type: Literal["connection_timeout"] = "connection_timeout"


SseEvent = (
    SseTextDelta
    | SseToolExecutionStarted
    | SseToolExecutionCompleted
    | SseStatus
    | SseError
    | SseAssistantTurnComplete
    | SsePing
    | SseResumeGenerated
    | SseResumeData
    | SseResumeScore
    | SseConnectionTimeout
    | SseThinkingDelta
    | SseSessionStarted
)


def sse_event_to_dict(event: SseEvent) -> dict[str, Any]:
    """将 SSE 事件序列化为字典。"""
    result: dict[str, Any] = {"type": event.type}  # type: ignore[attr-defined]
    if isinstance(event, SseTextDelta):
        result["text"] = event.text
    elif isinstance(event, SseToolExecutionStarted):
        result["tool_name"] = event.tool_name
        if event.tool_input is not None:
            result["tool_input"] = event.tool_input
    elif isinstance(event, SseToolExecutionCompleted):
        result["tool_name"] = event.tool_name
        result["output"] = event.output
        result["is_error"] = event.is_error
    elif isinstance(event, SseStatus):
        result["message"] = event.message
    elif isinstance(event, SseError):
        result["code"] = event.code
        result["message"] = event.message
    elif isinstance(event, SseAssistantTurnComplete):
        if event.usage is not None:
            result["usage"] = event.usage
    elif isinstance(event, SseResumeGenerated):
        result["resume_id"] = event.resume_id
    elif isinstance(event, SseResumeData):
        result["resume_id"] = event.resume_id
        if event.data is not None:
            result["data"] = event.data
        result["template_hint"] = event.template_hint
        if event.suggestions:
            result["suggestions"] = event.suggestions
        if event.resume_prefix:
            result["resume_prefix"] = event.resume_prefix
    elif isinstance(event, SseThinkingDelta):
        result["text"] = event.text
    elif isinstance(event, SseResumeScore):
        result["resume_id"] = event.resume_id
        result["score"] = event.score
        if event.dimensions is not None:
            result["dimensions"] = event.dimensions
        if event.suggestions is not None:
            result["suggestions"] = event.suggestions
        if event.jd_keywords_matched is not None:
            result["jd_keywords_matched"] = event.jd_keywords_matched
        if event.jd_keywords_missing is not None:
            result["jd_keywords_missing"] = event.jd_keywords_missing
    elif isinstance(event, SseSessionStarted):
        result["session_id"] = event.session_id
    return result


def format_sse_data(event: SseEvent) -> str:
    """格式化为 SSE data 行。"""
    import json
    return f"data: {json.dumps(sse_event_to_dict(event), ensure_ascii=False)}\n\n"
