"""上下文压缩服务，将长对话历史压缩为摘要以控制 Token 用量。

当对话消息总 Token 数接近 auto_compact_threshold_tokens 时，
自动将早期消息替换为一段摘要，保留最近的对话上下文。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from resume_agent.engine.messages import ConversationMessage, TextBlock

if TYPE_CHECKING:
    from resume_agent.api.client import SupportsStreamingMessages

log = logging.getLogger(__name__)

# 压缩提示词
_COMPACT_SYSTEM_PROMPT = """\
你是一个对话摘要助手。请将以下对话历史压缩为一段简洁的摘要，保留关键信息：
1. 用户的核心需求
2. 已完成的重要操作
3. 用户的偏好和反馈
4. 尚未完成的任务

摘要应尽量简短（不超过 500 字），但不要丢失重要信息。
"""

_COMPACT_USER_PROMPT = """\
请将以下对话历史压缩为一段摘要：

---
{conversation}
---

请直接输出摘要内容，不要额外解释。"""


def estimate_message_tokens(messages: list[ConversationMessage]) -> int:
    """粗略估算消息列表的 Token 数。

    使用简单的启发式规则：1 个中文字 ≈ 1 token，1 个英文单词 ≈ 1.3 token。
    这不是精确估算，但足够用于触发压缩判断。
    """
    total_chars = 0
    for msg in messages:
        for block in msg.content:
            if isinstance(block, TextBlock):
                total_chars += len(block.text)
            # ToolResultBlock 和 ToolUseBlock 也有文本内容
            elif hasattr(block, "content"):
                content = block.content  # type: ignore[attr-defined]
                if isinstance(content, str):
                    total_chars += len(content)
    # 粗略估算：平均每 3 个字符约 1 token
    return max(1, total_chars // 3)


def select_messages_to_compact(
    messages: list[ConversationMessage],
    *,
    keep_recent: int = 4,
) -> tuple[list[ConversationMessage], list[ConversationMessage]]:
    """将消息分为需要压缩的早期部分和保留的近期部分。

    Args:
        messages: 完整消息列表
        keep_recent: 保留最近 N 条消息不压缩

    Returns:
        (to_compact, to_keep) 元组
    """
    if len(messages) <= keep_recent:
        return [], messages

    split_idx = len(messages) - keep_recent
    return messages[:split_idx], messages[split_idx:]


def format_messages_for_compact(messages: list[ConversationMessage]) -> str:
    """将消息列表格式化为压缩提示词的输入文本。"""
    lines: list[str] = []
    for msg in messages:
        role = msg.role
        text = msg.text if hasattr(msg, "text") else ""
        if not text:
            # 尝试提取工具调用信息
            tool_uses = msg.tool_uses if hasattr(msg, "tool_uses") else []
            tool_results = [
                b for b in msg.content
                if hasattr(b, "content") and hasattr(b, "is_error")
            ]
            if tool_uses:
                for tu in tool_uses:
                    lines.append(f"[{role}] 调用工具: {tu.name}")
            elif tool_results:
                for tr in tool_results:
                    content = tr.content if hasattr(tr, "content") else ""
                    lines.append(f"[{role}] 工具结果: {content[:200]}")
            continue
        # 截断过长的消息
        if len(text) > 500:
            text = text[:500] + "..."
        lines.append(f"[{role}] {text}")
    return "\n".join(lines)


async def compact_messages(
    messages: list[ConversationMessage],
    api_client: SupportsStreamingMessages,
    model: str,
    *,
    keep_recent: int = 4,
    max_tokens: int = 1024,
) -> list[ConversationMessage]:
    """使用 LLM 将早期对话历史压缩为摘要。

    Args:
        messages: 完整消息列表
        api_client: API 客户端（用于调用 LLM 生成摘要）
        model: 使用的模型名称
        keep_recent: 保留最近 N 条消息不压缩
        max_tokens: 摘要生成的最大 Token 数

    Returns:
        压缩后的消息列表（摘要 + 近期消息）
    """
    from resume_agent.api.client import ApiMessageRequest

    to_compact, to_keep = select_messages_to_compact(messages, keep_recent=keep_recent)

    if not to_compact:
        return messages

    conversation_text = format_messages_for_compact(to_compact)
    user_prompt = _COMPACT_USER_PROMPT.format(conversation=conversation_text)

    # 调用 LLM 生成摘要
    summary_message = ConversationMessage(
        role="user",
        content=[TextBlock(text=user_prompt)],
    )

    summary_text = ""
    request = ApiMessageRequest(
        model=model,
        messages=[summary_message],
        system_prompt=_COMPACT_SYSTEM_PROMPT,
        max_tokens=max_tokens,
        tools=[],
    )

    try:
        from resume_agent.api.client import ApiMessageCompleteEvent, ApiTextDeltaEvent
        async for event in api_client.stream_message(request):
            if isinstance(event, ApiTextDeltaEvent):
                summary_text += event.text
    except Exception as exc:
        log.warning("上下文压缩失败，保留原始消息: %s", exc)
        return messages

    if not summary_text.strip():
        log.warning("上下文压缩返回空摘要，保留原始消息")
        return messages

    # 构建压缩后的消息列表
    compacted = [
        ConversationMessage(
            role="user",
            content=[TextBlock(text="[对话历史摘要]")],
        ),
        ConversationMessage(
            role="assistant",
            content=[TextBlock(text=summary_text.strip())],
        ),
    ]

    log.info(
        "上下文压缩完成: %d 条消息 → 摘要 %d 字符 + 保留 %d 条近期消息",
        len(to_compact),
        len(summary_text),
        len(to_keep),
    )

    return compacted + to_keep


def should_compact(
    messages: list[ConversationMessage],
    threshold_tokens: int | None = None,
) -> bool:
    """判断是否需要进行上下文压缩。

    Args:
        messages: 当前消息列表
        threshold_tokens: 压缩触发阈值（Token 数）

    Returns:
        True 表示需要压缩
    """
    if threshold_tokens is None or threshold_tokens <= 0:
        return False

    estimated = estimate_message_tokens(messages)
    return estimated >= threshold_tokens
