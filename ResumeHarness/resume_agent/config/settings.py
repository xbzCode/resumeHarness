"""全局/用户级配置加载（.env 文件 > 环境变量 > settings.json > 默认值）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from resume_agent.exceptions import ConfigurationError

# 在 import 时加载项目根目录下的 .env 文件
_project_root = Path(__file__).resolve().parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# 默认数据根目录
DEFAULT_DATA_ROOT = Path.home() / ".resume_agent"


class McpServerConfig(BaseModel):
    """MCP 服务器配置。"""

    type: str = "http"  # 仅 HTTP
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True  # 是否启用


# 默认 MCP 服务器配置
DEFAULT_MCP_SERVERS: dict[str, dict[str, Any]] = {
    "pdf": {
        "type": "http",
        "url": "http://127.0.0.1:9100",
        "enabled": True,
    },
    "email": {
        "type": "http",
        "url": "http://127.0.0.1:9101",
        "enabled": True,
    },
    "jd": {
        "type": "http",
        "url": "http://127.0.0.1:9102",
        "enabled": True,
    },
}


class ResumeAgentSettings(BaseModel):
    """Resume Agent 全局配置。"""

    # API 配置
    api_format: str = "openai"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    api_key: str = ""
    api_keys: list[str] = Field(default_factory=list)
    timeout: float = 30.0
    max_tokens: int = 4096
    context_window_tokens: int | None = None
    auto_compact_threshold_tokens: int | None = None
    max_turns: int = 200

    # httpx 连接池配置
    httpx_pool_max_connections: int = 100  # 最大连接数
    httpx_pool_max_keepalive: int = 20  # 最大 keep-alive 连接数
    httpx_connect_timeout: float = 10.0  # 连接超时（秒）

    # 会话池配置
    max_sessions: int = 20
    idle_timeout: int = 1800  # 秒

    # 记忆配置
    memory_max_files: int = 5
    memory_max_entry_lines: int = 200
    memory_resume_max_bytes: int = 16384  # 简历原文最大 16KB
    memory_other_max_bytes: int = 4096  # 其他记忆文件最大 4KB
    memory_max_history_entries: int = 10  # 优化历史最多 10 条
    memory_max_inject_tokens: int = 8000  # 总记忆注入不超过 8K tokens

    # 速率限制配置
    rate_limit_enabled: bool = True  # 是否启用速率限制
    rate_limit_rpm: int = 20  # 每用户每分钟请求限制
    rate_limit_max_wait: float = 5.0  # 速率限制最大等待时间（秒）

    # 监控配置
    monitor_enabled: bool = True  # 是否启用基础监控
    monitor_log_interval: int = 60  # 监控日志汇总间隔（秒）

    # MCP 服务器配置
    mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)

    @property
    def data_root(self) -> Path:
        """获取数据根目录。"""
        env_root = os.environ.get("RESUME_AGENT_DATA_ROOT", "")
        if env_root:
            return Path(env_root)
        return DEFAULT_DATA_ROOT

    @property
    def effective_api_keys(self) -> list[str]:
        """获取有效的 API Key 列表（合并 api_key 和 api_keys）。"""
        keys = list(self.api_keys)
        # 环境变量中的 key
        env_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if env_key and env_key not in keys:
            keys.insert(0, env_key)
        # settings 中的单 key
        if self.api_key and self.api_key not in keys:
            keys.insert(0, self.api_key)
        return keys

    @property
    def effective_base_url(self) -> str:
        """获取有效的 Base URL。"""
        return os.environ.get("DEEPSEEK_BASE_URL", "") or self.base_url

    @property
    def effective_model(self) -> str:
        """获取有效的模型名。"""
        return os.environ.get("DEEPSEEK_MODEL", "") or self.model

    def get_user_dir(self, user_id: str) -> Path:
        """获取用户数据目录。"""
        return self.data_root / "users" / user_id

    def get_user_memory_dir(self, user_id: str) -> Path:
        """获取用户记忆目录。"""
        path = self.get_user_dir(user_id) / "memory"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_user_sessions_dir(self, user_id: str) -> Path:
        """获取用户会话目录。"""
        path = self.get_user_dir(user_id) / "sessions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_user_resumes_dir(self, user_id: str) -> Path:
        """获取用户简历目录。"""
        path = self.get_user_dir(user_id) / "resumes"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_user_settings_path(self, user_id: str) -> Path:
        """获取用户级配置文件路径。"""
        return self.get_user_dir(user_id) / "settings.json"


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

_settings_instance: ResumeAgentSettings | None = None


def _settings_file_path() -> Path:
    """获取全局配置文件路径。"""
    return DEFAULT_DATA_ROOT / "settings.json"


def load_settings() -> ResumeAgentSettings:
    """加载配置（环境变量 > settings.json > 默认值）。"""
    global _settings_instance

    path = _settings_file_path()
    raw: dict[str, Any] = {}

    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}

    # 合并默认 MCP 服务器配置
    if "mcp_servers" not in raw:
        raw["mcp_servers"] = DEFAULT_MCP_SERVERS
    else:
        # 用户配置覆盖默认值，但保留未覆盖的默认服务器
        merged_servers = dict(DEFAULT_MCP_SERVERS)
        merged_servers.update(raw["mcp_servers"])
        raw["mcp_servers"] = merged_servers

    settings = ResumeAgentSettings.model_validate(raw)

    # 应用环境变量覆盖
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        settings = settings.model_copy(update={"api_key": env_key})

    _settings_instance = settings
    return settings


def get_settings() -> ResumeAgentSettings:
    """获取当前配置实例（懒加载）。"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = load_settings()
    return _settings_instance


def validate_api_config() -> None:
    """启动时校验 API 配置，缺少必要配置则抛出异常拒绝启动。"""
    settings = get_settings()
    if not settings.effective_api_keys:
        raise ConfigurationError(
            "DeepSeek API Key 未配置。请复制 .env.example 为 .env "
            "并填写 DEEPSEEK_API_KEY，或设置环境变量 DEEPSEEK_API_KEY。"
        )


# ---------------------------------------------------------------------------
# 用户级 Settings
# ---------------------------------------------------------------------------

class UserSettings(BaseModel):
    """用户级配置，可覆盖全局配置中的非敏感项。"""

    # 简历模板偏好
    default_template: str = "professional"

    # 语言风格
    language_style: str = "professional"  # professional / casual / academic

    # 输出语言
    output_language: str = "zh-CN"

    # 是否自动保存简历快照
    auto_save_resume: bool = True


def load_user_settings(user_id: str) -> UserSettings:
    """加载用户级配置。"""
    settings = get_settings()
    path = settings.get_user_settings_path(user_id)

    raw: dict[str, Any] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}

    return UserSettings.model_validate(raw)


def save_user_settings(user_id: str, user_settings: UserSettings) -> Path:
    """保存用户级配置。"""
    settings = get_settings()
    path = settings.get_user_settings_path(user_id)

    # 确保用户目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    data = user_settings.model_dump(mode="json", exclude_defaults=False)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
