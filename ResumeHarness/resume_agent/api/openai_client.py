"""OpenAI-compatible API client for DeepSeek and similar providers.

从 OpenHarness 裁剪而来，移除了 Anthropic 特有逻辑。
优化：多 Key 场景下为每个 Key 预创建独立的 AsyncOpenAI 客户端，避免连接泄露。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

import httpx
from openai import AsyncOpenAI

from resume_agent.api.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiReasoningDeltaEvent,
    ApiRetryEvent,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from resume_agent.api.errors import (
    AuthenticationFailure,
    RateLimitFailure,
    RequestFailure,
    ResumeAgentApiError,
)
from resume_agent.api.usage import UsageSnapshot
from resume_agent.engine.messages import (
    ConversationMessage,
    ContentBlock,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

if TYPE_CHECKING:
    from resume_agent.api_key_pool import ApiKeyPool

log = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0


def _token_limit_param_for_model(model: str, max_tokens: int) -> dict[str, int]:
    """Return the correct token limit field for the target OpenAI model."""
    normalized = model.strip().lower()
    if "/" in normalized:
        normalized = normalized.rsplit("/", 1)[-1]
    if normalized.startswith(("gpt-5", "o1", "o3", "o4")):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def _convert_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool schemas to OpenAI function-calling format."""
    result = []
    for tool in tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return result


def _convert_messages_to_openai(
    messages: list[ConversationMessage],
    system_prompt: str | None,
) -> list[dict[str, Any]]:
    """Convert messages to OpenAI chat format."""
    openai_messages: list[dict[str, Any]] = []

    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        if msg.role == "assistant":
            openai_msg = _convert_assistant_message(msg)
            openai_messages.append(openai_msg)
        elif msg.role == "user":
            tool_results = [b for b in msg.content if isinstance(b, ToolResultBlock)]
            user_blocks = [b for b in msg.content if isinstance(b, (TextBlock, ImageBlock))]

            if tool_results:
                for tr in tool_results:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tr.tool_use_id,
                        "content": tr.content,
                    })
            if user_blocks:
                content = _convert_user_content_to_openai(user_blocks)
                if isinstance(content, str):
                    if content.strip():
                        openai_messages.append({"role": "user", "content": content})
                elif content:
                    openai_messages.append({"role": "user", "content": content})
            if not tool_results and not user_blocks:
                openai_messages.append({"role": "user", "content": ""})

    return openai_messages


def _convert_user_content_to_openai(blocks: list[ContentBlock]) -> str | list[dict[str, Any]]:
    """Convert user text/image blocks into OpenAI chat content."""
    has_image = any(isinstance(block, ImageBlock) for block in blocks)
    if not has_image:
        return "".join(block.text for block in blocks if isinstance(block, TextBlock))

    content: list[dict[str, Any]] = []
    for block in blocks:
        if isinstance(block, TextBlock) and block.text:
            content.append({"type": "text", "text": block.text})
        elif isinstance(block, ImageBlock):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{block.media_type};base64,{block.data}",
                },
            })
    return content


def _convert_assistant_message(msg: ConversationMessage) -> dict[str, Any]:
    """Convert an assistant ConversationMessage to OpenAI format."""
    text_parts = [b.text for b in msg.content if isinstance(b, TextBlock)]
    tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]

    openai_msg: dict[str, Any] = {"role": "assistant"}

    content = "".join(text_parts)
    openai_msg["content"] = content if content else None

    reasoning = getattr(msg, "_reasoning", None)
    if reasoning:
        openai_msg["reasoning_content"] = reasoning
    elif tool_uses:
        openai_msg["reasoning_content"] = ""

    if tool_uses:
        openai_msg["tool_calls"] = [
            {
                "id": tu.id,
                "type": "function",
                "function": {
                    "name": tu.name,
                    "arguments": json.dumps(tu.input),
                },
            }
            for tu in tool_uses
        ]

    return openai_msg


def _normalize_openai_base_url(base_url: str | None) -> str | None:
    """Normalize custom OpenAI-compatible base URLs."""
    if not base_url:
        return None
    trimmed = base_url.strip()
    if not trimmed:
        return None
    parts = urlsplit(trimmed)
    if not parts.scheme or not parts.netloc:
        return trimmed.rstrip("/")
    path = parts.path.rstrip("/")
    if not path:
        path = "/v1"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


class OpenAICompatibleClient:
    """Client for OpenAI-compatible APIs (DeepSeek, etc.).

    Implements the SupportsStreamingMessages protocol.
    Supports ApiKeyPool for multi-key rotation.

    优化：多 Key 场景下为每个 Key 预创建独立的 AsyncOpenAI 客户端，
    轮询时直接切换客户端引用，避免每次请求重建 httpx 连接池导致泄露。
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        key_pool: ApiKeyPool | None = None,
        pool_max_connections: int = 100,
        pool_max_keepalive: int = 20,
    ) -> None:
        self._initial_api_key = api_key
        self._key_pool = key_pool
        self._current_key = api_key
        self._base_url = _normalize_openai_base_url(base_url)
        self._timeout = timeout
        self._pool_max_connections = pool_max_connections
        self._pool_max_keepalive = pool_max_keepalive

        # 预创建共享的 httpx 连接池（所有 AsyncOpenAI 客户端复用）
        self._http_client: httpx.AsyncClient | None = None

        # 为每个 Key 预创建 AsyncOpenAI 客户端，避免轮询时重建
        self._clients: dict[str, AsyncOpenAI] = {}
        self._client = self._create_client(api_key)

        # 如果启用了 Key 轮询，预创建所有 Key 的客户端
        if key_pool is not None:
            for key in key_pool._keys:
                self._clients[key] = self._create_client(key)

    def _create_client(self, api_key: str) -> AsyncOpenAI:
        """创建一个 AsyncOpenAI 客户端实例（复用 httpx 连接池）。"""
        kwargs: dict[str, Any] = {"api_key": api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        if self._timeout is not None:
            kwargs["timeout"] = self._timeout

        # 使用共享的 httpx 连接池
        http_client = self._get_http_client()
        kwargs["http_client"] = http_client

        client = AsyncOpenAI(**kwargs)
        self._clients[api_key] = client
        return client

    def _get_http_client(self) -> httpx.AsyncClient:
        """获取或创建共享的 httpx.AsyncClient（连接池复用）。"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=self._pool_max_connections,
                    max_keepalive_connections=self._pool_max_keepalive,
                ),
                timeout=httpx.Timeout(
                    timeout=self._timeout or 30.0,
                    connect=10.0,
                ),
            )
        return self._http_client

    async def aclose(self) -> None:
        """关闭共享的 httpx 连接池，释放资源。应在应用关闭时调用。"""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
        self._clients.clear()
        log.info("OpenAICompatibleClient 连接池已关闭")

    async def stream_message(self, request: ApiMessageRequest) -> AsyncIterator[ApiStreamEvent]:
        """Yield text deltas and the final message, matching the client interface."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                # 从 pool 获取可用 Key（若启用轮询），切换到对应的预创建客户端
                if self._key_pool is not None:
                    self._current_key = await self._key_pool.acquire()
                    # 直接复用预创建的客户端，无需重建
                    self._client = self._clients.get(self._current_key, self._client)

                async for event in self._stream_once(request):
                    yield event
                return
            except ResumeAgentApiError:
                raise
            except Exception as exc:
                last_error = exc

                # 收到 429 时报告给 pool
                status = getattr(exc, "status_code", None)
                if status == 429 and self._key_pool is not None:
                    self._key_pool.report_429(self._current_key)

                if attempt >= MAX_RETRIES or not self._is_retryable(exc):
                    raise self._translate_error(exc) from exc

                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                log.warning(
                    "OpenAI API request failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, MAX_RETRIES + 1, delay, exc,
                )
                yield ApiRetryEvent(
                    message=str(exc),
                    attempt=attempt + 1,
                    max_attempts=MAX_RETRIES + 1,
                    delay_seconds=delay,
                )
                await asyncio.sleep(delay)

        if last_error is not None:
            raise self._translate_error(last_error) from last_error

    async def _stream_once(self, request: ApiMessageRequest) -> AsyncIterator[ApiStreamEvent]:
        """Single attempt: stream an OpenAI chat completion.

        当 finish_reason=length 时自动续写，避免长输出被截断。
        """
        openai_messages = _convert_messages_to_openai(request.messages, request.system_prompt)
        openai_tools = _convert_tools_to_openai(request.tools) if request.tools else None

        # 自动续写：当 finish_reason=length 时，将已输出内容追加到消息列表，
        # 发送"继续"提示让模型补全剩余内容。最多续写 5 次。
        max_continuations = 5
        continuation_count = 0

        collected_content = ""
        collected_reasoning = ""
        collected_tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        usage_data: dict[str, int] = {}

        # 构建当前轮次的请求消息（续写时会追加）
        current_messages = list(openai_messages)

        while True:
            params: dict[str, Any] = {
                "model": request.model,
                "messages": current_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            params.update(_token_limit_param_for_model(request.model, request.max_tokens))
            if openai_tools:
                params["tools"] = openai_tools
                params.pop("stream_options", None)

            round_content = ""
            round_reasoning = ""
            round_tool_calls: dict[int, dict[str, Any]] = {}
            round_finish: str | None = None

            stream = await self._client.chat.completions.create(**params)
            async for chunk in stream:
                if not chunk.choices:
                    if chunk.usage:
                        usage_data = {
                            "input_tokens": usage_data.get("input_tokens", 0) + (chunk.usage.prompt_tokens or 0),
                            "output_tokens": usage_data.get("output_tokens", 0) + (chunk.usage.completion_tokens or 0),
                        }
                    continue

                delta = chunk.choices[0].delta
                chunk_finish = chunk.choices[0].finish_reason

                if chunk_finish:
                    round_finish = chunk_finish

                reasoning_piece = getattr(delta, "reasoning_content", None) or ""
                if reasoning_piece:
                    round_reasoning += reasoning_piece
                    collected_reasoning += reasoning_piece
                    yield ApiReasoningDeltaEvent(text=reasoning_piece)

                if delta.content:
                    round_content += delta.content
                    collected_content += delta.content
                    yield ApiTextDeltaEvent(text=delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in round_tool_calls:
                            round_tool_calls[idx] = {
                                "id": tc_delta.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        entry = round_tool_calls[idx]
                        if tc_delta.id:
                            entry["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                entry["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                entry["arguments"] += tc_delta.function.arguments

                if chunk.usage:
                    usage_data = {
                        "input_tokens": usage_data.get("input_tokens", 0) + (chunk.usage.prompt_tokens or 0),
                        "output_tokens": usage_data.get("output_tokens", 0) + (chunk.usage.completion_tokens or 0),
                    }

            # 合并本轮的 tool_calls
            for idx, tc in round_tool_calls.items():
                if idx not in collected_tool_calls:
                    collected_tool_calls[idx] = tc
                else:
                    existing = collected_tool_calls[idx]
                    if tc["id"]:
                        existing["id"] = tc["id"]
                    if tc["name"]:
                        existing["name"] = tc["name"]
                    if tc["arguments"]:
                        existing["arguments"] += tc["arguments"]

            finish_reason = round_finish

            # 检查是否需要续写：finish_reason=length 且没有 tool_calls
            if (
                round_finish == "length"
                and not round_tool_calls
                and continuation_count < max_continuations
            ):
                continuation_count += 1
                log.info(
                    "输出被 max_tokens 截断（finish_reason=length），自动续写第 %d 次",
                    continuation_count,
                )
                # 将已输出的 assistant 消息追加到上下文
                assistant_msg: dict[str, Any] = {"role": "assistant", "content": round_content}
                if round_reasoning:
                    assistant_msg["reasoning_content"] = round_reasoning
                current_messages.append(assistant_msg)
                # 追加"继续"提示
                current_messages.append({"role": "user", "content": "请继续输出，不要重复已经输出的内容。"})
                continue
            else:
                break

        content: list[ContentBlock] = []
        if collected_content:
            content.append(TextBlock(text=collected_content))

        for _idx in sorted(collected_tool_calls.keys()):
            tc = collected_tool_calls[_idx]
            if not tc["name"]:
                continue
            try:
                args = json.loads(tc["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            content.append(ToolUseBlock(
                id=tc["id"],
                name=tc["name"],
                input=args,
            ))

        final_message = ConversationMessage(role="assistant", content=content)

        if collected_reasoning:
            final_message._reasoning = collected_reasoning  # type: ignore[attr-defined]

        yield ApiMessageCompleteEvent(
            message=final_message,
            usage=UsageSnapshot(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            ),
            stop_reason=finish_reason,
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        if status and status in {429, 500, 502, 503}:
            return True
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return True
        return False

    @staticmethod
    def _translate_error(exc: Exception) -> ResumeAgentApiError:
        status = getattr(exc, "status_code", None)
        msg = str(exc)
        if status == 401 or status == 403:
            return AuthenticationFailure(msg)
        if status == 429:
            return RateLimitFailure(msg)
        return RequestFailure(msg)
