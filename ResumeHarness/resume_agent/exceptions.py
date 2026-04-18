"""统一错误码与异常定义。"""

from __future__ import annotations


class ResumeAgentError(Exception):
    """Resume Agent 基础异常。"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ConfigurationError(ResumeAgentError):
    """配置错误。"""

    def __init__(self, message: str) -> None:
        super().__init__(code=1000, message=message)


class AuthenticationError(ResumeAgentError):
    """认证错误（P2 阶段启用）。"""

    def __init__(self, message: str = "用户未认证") -> None:
        super().__init__(code=1001, message=message)


class TokenExpiredError(ResumeAgentError):
    """Token 过期。"""

    def __init__(self, message: str = "Token 过期") -> None:
        super().__init__(code=1002, message=message)


class ApiCallError(ResumeAgentError):
    """DeepSeek API 调用失败。"""

    def __init__(self, message: str) -> None:
        super().__init__(code=2001, message=message)


class RateLimitError(ResumeAgentError):
    """速率限制。"""

    def __init__(self, message: str = "速率限制，请稍后重试") -> None:
        super().__init__(code=2002, message=message)


class SessionNotFoundError(ResumeAgentError):
    """会话不存在。"""

    def __init__(self, message: str = "会话不存在") -> None:
        super().__init__(code=3001, message=message)


class SessionExpiredError(ResumeAgentError):
    """会话已过期。"""

    def __init__(self, message: str = "会话已过期") -> None:
        super().__init__(code=3002, message=message)


class McpUnavailableError(ResumeAgentError):
    """MCP 服务不可用。"""

    def __init__(self, message: str = "MCP 服务不可用") -> None:
        super().__init__(code=4001, message=message)


class ResumeRenderError(ResumeAgentError):
    """简历渲染失败。"""

    def __init__(self, message: str) -> None:
        super().__init__(code=4002, message=message)


class ResumeNotFoundError(ResumeAgentError):
    """简历不存在。"""

    def __init__(self, message: str = "简历不存在") -> None:
        super().__init__(code=4003, message=message)


class MemoryNotFoundError(ResumeAgentError):
    """记忆文档不存在。"""

    def __init__(self, message: str = "记忆文档不存在") -> None:
        super().__init__(code=5001, message=message)


class WebFetchError(ResumeAgentError):
    """网页抓取失败。"""

    def __init__(self, message: str) -> None:
        super().__init__(code=6001, message=message)
