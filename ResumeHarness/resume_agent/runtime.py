"""精简版 RuntimeBundle 构建，跳过本地工具和 MCP stdio。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from resume_agent.api.client import SupportsStreamingMessages
from resume_agent.api.openai_client import OpenAICompatibleClient
from resume_agent.engine.messages import ConversationMessage
from resume_agent.engine.query_engine import QueryEngine
from resume_agent.engine.stream_events import StreamEvent
from resume_agent.hooks.executor import HookExecutor
from resume_agent.hooks.loader import HookRegistry
from resume_agent.permissions.checker import PermissionChecker
from resume_agent.permissions.modes import PermissionMode
from resume_agent.tools.base import ToolRegistry

from resume_agent.api_key_pool import ApiKeyPool
from resume_agent.config.settings import ResumeAgentSettings, get_settings, validate_api_config
from resume_agent.exceptions import ConfigurationError

log = logging.getLogger(__name__)


@dataclass
class RuntimeBundle:
    """精简版运行时 Bundle，包含 QueryEngine 及其依赖。"""

    engine: QueryEngine
    api_client: SupportsStreamingMessages
    tool_registry: ToolRegistry
    permission_checker: PermissionChecker
    hook_executor: HookExecutor | None
    user_id: str
    session_id: str
    model: str
    system_prompt: str


# ---------------------------------------------------------------------------
# 进程级单例（跨会话共享）
# ---------------------------------------------------------------------------

_shared_api_client: OpenAICompatibleClient | None = None
_shared_tool_registry: ToolRegistry | None = None
_shared_hook_executor: HookExecutor | None = None
_shared_key_pool: ApiKeyPool | None = None


def _get_shared_key_pool(settings: ResumeAgentSettings) -> ApiKeyPool:
    """获取进程级 ApiKeyPool 单例。"""
    global _shared_key_pool
    if _shared_key_pool is None:
        _shared_key_pool = ApiKeyPool(
            api_keys=settings.effective_api_keys,
            rpm_per_key=30,
        )
    return _shared_key_pool


def _get_shared_api_client(settings: ResumeAgentSettings) -> OpenAICompatibleClient:
    """获取进程级 OpenAICompatibleClient 单例。"""
    global _shared_api_client
    if _shared_api_client is None:
        _shared_api_client = OpenAICompatibleClient(
            api_key=settings.effective_api_keys[0],
            base_url=settings.effective_base_url,
            timeout=settings.timeout,
        )
    return _shared_api_client


def _get_shared_tool_registry() -> ToolRegistry:
    """获取进程级 ToolRegistry 单例。"""
    global _shared_tool_registry
    if _shared_tool_registry is None:
        _shared_tool_registry = ToolRegistry()
    return _shared_tool_registry


def _get_shared_hook_executor() -> HookExecutor | None:
    """获取进程级 HookExecutor 单例。P0 阶段暂不加载 hooks。"""
    global _shared_hook_executor
    if _shared_hook_executor is None:
        registry = HookRegistry()
        _shared_hook_executor = HookExecutor(registry=registry)
    return _shared_hook_executor


def _build_auto_permission_checker() -> PermissionChecker:
    """构建固定 AUTO 模式的权限检查器。"""
    return PermissionChecker(mode=PermissionMode.FULL_AUTO)


async def build_resume_runtime(
    *,
    user_id: str,
    session_id: str | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    extra_skill_dirs: tuple[str, ...] = (),
) -> RuntimeBundle:
    """构建精简版 RuntimeBundle，跳过本地工具和 MCP stdio。

    与原版 build_runtime() 的差异：
    - API Client: 仅 OpenAICompatibleClient → DeepSeek
    - Tool Registry: 仅 MCP 工具 + skill 工具 + web_fetch + memory_write
    - Permission: 固定 AUTO 模式
    - Hook: 仅全局 hooks (P0 暂空)
    - 不创建 Sandbox / Swarm
    - System Prompt: 注入用户记忆 + resume-skill.md
    """
    settings = get_settings()
    validate_api_config()

    # 确定参数
    sid = session_id or "default"
    effective_model = model or settings.effective_model

    # 构建系统提示词
    effective_prompt = system_prompt
    if effective_prompt is None:
        from resume_agent.prompts import build_resume_system_prompt
        effective_prompt = await build_resume_system_prompt(user_id)

    # 获取共享单例
    api_client = _get_shared_api_client(settings)
    tool_registry = _get_shared_tool_registry()
    permission_checker = _build_auto_permission_checker()
    hook_executor = _get_shared_hook_executor()

    # 创建 QueryEngine（每会话独立）
    engine = QueryEngine(
        api_client=api_client,
        tool_registry=tool_registry,
        permission_checker=permission_checker,
        cwd=settings.data_root,
        model=effective_model,
        system_prompt=effective_prompt,
        max_tokens=settings.max_tokens,
        context_window_tokens=settings.context_window_tokens,
        auto_compact_threshold_tokens=settings.auto_compact_threshold_tokens,
        max_turns=settings.max_turns,
        permission_prompt=None,
        ask_user_prompt=None,
        hook_executor=hook_executor,
        tool_metadata={},
    )

    return RuntimeBundle(
        engine=engine,
        api_client=api_client,
        tool_registry=tool_registry,
        permission_checker=permission_checker,
        hook_executor=hook_executor,
        user_id=user_id,
        session_id=sid,
        model=effective_model,
        system_prompt=effective_prompt,
    )


async def submit_message(
    bundle: RuntimeBundle,
    prompt: str,
) -> list[StreamEvent]:
    """向 RuntimeBundle 提交一条消息并收集所有流式事件。"""
    events: list[StreamEvent] = []
    async for event in bundle.engine.submit_message(prompt):
        events.append(event)
    return events


def reset_shared_instances() -> None:
    """重置所有进程级单例（主要用于测试）。"""
    global _shared_api_client, _shared_tool_registry, _shared_hook_executor, _shared_key_pool
    _shared_api_client = None
    _shared_tool_registry = None
    _shared_hook_executor = None
    _shared_key_pool = None
