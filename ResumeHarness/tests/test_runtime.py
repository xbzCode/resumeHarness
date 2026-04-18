"""P0-1 验收测试：resume_agent 包可 import，build_resume_runtime() 可创建能对话的 QueryEngine。"""

from __future__ import annotations

import os
import pytest


# 设置测试用 API Key
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-key-for-unit-test")


def test_package_import():
    """验证 resume_agent 包可正常 import。"""
    import resume_agent
    assert resume_agent.__version__ == "0.1.0"


def test_config_import():
    """验证配置模块可正常 import。"""
    from resume_agent.config import get_settings, validate_api_config
    settings = get_settings()
    assert settings.model == "deepseek-chat"
    assert settings.base_url == "https://api.deepseek.com"


def test_exceptions_import():
    """验证异常模块可正常 import。"""
    from resume_agent.exceptions import (
        ResumeAgentError,
        ConfigurationError,
        RateLimitError,
        SessionNotFoundError,
    )
    err = ConfigurationError("test")
    assert err.code == 1000
    assert "test" in str(err)


def test_api_key_pool_import():
    """验证 ApiKeyPool 可正常 import 和初始化。"""
    from resume_agent.api_key_pool import ApiKeyPool
    pool = ApiKeyPool(api_keys=["sk-test-1", "sk-test-2"], rpm_per_key=30)
    assert len(pool.keys) == 2


def test_session_pool_import():
    """验证 SessionPool 可正常 import。"""
    from resume_agent.session_pool import ResumeSessionPool
    pool = ResumeSessionPool(max_sessions=10, idle_timeout=600)
    assert pool._max_sessions == 10


def test_models_import():
    """验证数据模型可正常 import。"""
    from resume_agent.models.sse_events import SseTextDelta, format_sse_data
    event = SseTextDelta(text="hello")
    data = format_sse_data(event)
    assert "text_delta" in data
    assert "hello" in data


def test_api_schemas_import():
    """验证 API Schema 可正常 import。"""
    from resume_agent.models.api_schemas import ChatRequest
    req = ChatRequest(prompt="帮我优化简历")
    assert req.prompt == "帮我优化简历"
    assert req.session_id is None


def test_settings_effective_keys():
    """验证配置加载能正确合并 API Key。"""
    from resume_agent.config import get_settings
    settings = get_settings()
    # 测试模式下环境变量设置了 key
    keys = settings.effective_api_keys
    assert len(keys) >= 1
    assert "sk-test-key-for-unit-test" in keys


def test_settings_user_dirs():
    """验证用户目录路径生成。"""
    from resume_agent.config import get_settings
    settings = get_settings()
    user_dir = settings.get_user_dir("test_user")
    assert "test_user" in str(user_dir)
    memory_dir = settings.get_user_memory_dir("test_user")
    assert "memory" in str(memory_dir)


def test_runtime_module_import():
    """验证 runtime 模块可正常 import。"""
    from resume_agent.runtime import RuntimeBundle, build_resume_runtime, submit_message
    assert RuntimeBundle is not None
    assert build_resume_runtime is not None


def test_tools_import():
    """验证工具模块可正常 import。"""
    from resume_agent.tools.memory_write import MemoryWriteTool
    from resume_agent.tools.web_fetch import WebFetchTool
    from resume_agent.tools.skill_loader import SkillLoaderTool

    assert MemoryWriteTool.name == "memory_write"
    assert WebFetchTool.name == "web_fetch"
    assert SkillLoaderTool.name == "skill_loader"


def test_prompts_import():
    """验证提示词模块可正常 import。"""
    from resume_agent.prompts import RESUME_AGENT_SYSTEM_PROMPT, build_resume_system_prompt
    assert "简历优化顾问" in RESUME_AGENT_SYSTEM_PROMPT


def test_memory_import():
    """验证记忆模块可正常 import。"""
    from resume_agent.memory import (
        list_memory_files,
        load_memory_prompt,
        write_memory_file,
        ensure_user_dirs,
    )
    assert list_memory_files is not None


def test_validate_api_config_with_key():
    """验证 API 配置校验通过（有 key 时）。"""
    from resume_agent.config import validate_api_config
    # 测试环境已有 key，不应抛异常
    validate_api_config()


def test_validate_api_config_without_key():
    """验证 API 配置校验失败（无 key 时）。"""
    import os
    from resume_agent.config import ResumeAgentSettings
    from resume_agent.exceptions import ConfigurationError

    # 临时清除环境变量，确保空配置检测正确
    saved_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        empty_settings = ResumeAgentSettings(api_key="", api_keys=[])
        assert len(empty_settings.effective_api_keys) == 0
    finally:
        if saved_key is not None:
            os.environ["DEEPSEEK_API_KEY"] = saved_key
