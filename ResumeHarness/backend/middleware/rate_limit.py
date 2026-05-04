"""用户级 API 速率限制中间件。

按 user_id 维护令牌桶，防止单用户过度消耗 API 配额。
对 /api/chat 端点强制限制，对其他 API 端点宽松限制。
"""

from __future__ import annotations

import json
import logging
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from resume_agent.services.rate_limiter import UserRateLimiter

logger = logging.getLogger(__name__)

# 不同路径的速率限制倍率
_PATH_MULTIPLIERS: dict[str, float] = {
    "/api/chat": 1.0,  # 对话端点：完整限制
}

# 默认倍率（非对话端点使用更宽松的限制）
_DEFAULT_MULTIPLIER = 3.0


class RateLimitMiddleware:
    """用户级 API 速率限制中间件（纯 ASGI 实现）。"""

    def __init__(self, app: ASGIApp, rpm: int = 20, max_wait: float = 5.0) -> None:
        self.app = app
        self._limiter = UserRateLimiter(rpm=rpm)
        self._max_wait = max_wait

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # 非 API 路径直接放行
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        # 公开路径放行
        public_prefixes = (
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
        )
        for prefix in public_prefixes:
            if path.startswith(prefix):
                await self.app(scope, receive, send)
                return

        # OPTIONS 请求放行
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # 获取 user_id（认证中间件已注入到 scope["state"]）
        state = scope.get("state", {})
        user_id = state.get("user_id")
        if not user_id:
            # 未认证请求，不限制（由 AuthMiddleware 拦截）
            await self.app(scope, receive, send)
            return

        # 非对话端点使用更宽松的限制
        multiplier = _DEFAULT_MULTIPLIER
        for prefix, mult in _PATH_MULTIPLIERS.items():
            if path.startswith(prefix):
                multiplier = mult
                break

        # 尝试获取令牌
        if multiplier > 1.0:
            if not self._limiter.try_acquire(user_id):
                status = self._limiter.get_status(user_id)
                if status.get("tokens_available", 0) < -5:
                    await self._send_rate_limit(send)
                    return
            await self.app(scope, receive, send)
            return

        # 对话端点：严格限制
        if not self._limiter.try_acquire(user_id):
            logger.warning("速率限制触发: user=%s path=%s", user_id, path)
            await self._send_rate_limit(send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_rate_limit(send: Send) -> None:
        """发送 429 速率限制响应。"""
        body_dict = {
            "detail": "请求过于频繁，请稍后重试",
            "code": 2002,
            "retry_after": 3,
        }
        body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
                [b"retry-after", b"3"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    def get_limiter(self) -> UserRateLimiter:
        """获取底层限速器实例（供状态查询 API 使用）。"""
        return self._limiter
