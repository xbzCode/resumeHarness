"""用户级 API 速率限制中间件。

按 user_id 维护令牌桶，防止单用户过度消耗 API 配额。
对 /api/chat 端点强制限制，对其他 API 端点宽松限制。
"""

from __future__ import annotations

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from resume_agent.services.rate_limiter import UserRateLimiter

logger = logging.getLogger(__name__)

# 不同路径的速率限制倍率
_PATH_MULTIPLIERS: dict[str, float] = {
    "/api/chat": 1.0,  # 对话端点：完整限制
}

# 默认倍率（非对话端点使用更宽松的限制）
_DEFAULT_MULTIPLIER = 3.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """用户级 API 速率限制中间件。"""

    def __init__(self, app, rpm: int = 20, max_wait: float = 5.0) -> None:
        super().__init__(app)
        self._limiter = UserRateLimiter(rpm=rpm)
        self._max_wait = max_wait

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # 非 API 路径直接放行
        if not path.startswith("/api/"):
            return await call_next(request)

        # 公开路径放行（与 AuthMiddleware 一致）
        public_prefixes = (
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
        )
        for prefix in public_prefixes:
            if path.startswith(prefix):
                return await call_next(request)

        # OPTIONS 请求放行
        if request.method == "OPTIONS":
            return await call_next(request)

        # 获取 user_id（认证中间件已注入）
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # 未认证请求，不限制（由 AuthMiddleware 拦截）
            return await call_next(request)

        # 非对话端点使用更宽松的限制
        multiplier = _DEFAULT_MULTIPLIER
        for prefix, mult in _PATH_MULTIPLIERS.items():
            if path.startswith(prefix):
                multiplier = mult
                break

        # 尝试获取令牌（非阻塞）
        # 对非对话端点，使用宽松倍率
        if multiplier > 1.0:
            # 简单策略：非对话端点不做严格限制，仅检查极端情况
            # 如果对话端点的令牌已耗尽，其他端点也受限
            if not self._limiter.try_acquire(user_id):
                # 对非对话端点，允许一定超限
                status = self._limiter.get_status(user_id)
                # 如果令牌极度不足（< -5），才限制
                if status.get("tokens_available", 0) < -5:
                    return self._rate_limit_response(user_id, path)
            return await call_next(request)

        # 对话端点：严格限制
        if not self._limiter.try_acquire(user_id):
            logger.warning("速率限制触发: user=%s path=%s", user_id, path)
            return self._rate_limit_response(user_id, path)

        return await call_next(request)

    @staticmethod
    def _rate_limit_response(user_id: str, path: str) -> Response:
        """返回 429 速率限制响应。"""
        import json

        body = {
            "detail": "请求过于频繁，请稍后重试",
            "code": 2002,
            "retry_after": 3,  # 建议等待秒数
        }
        return Response(
            content=json.dumps(body, ensure_ascii=False),
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "3"},
        )

    def get_limiter(self) -> UserRateLimiter:
        """获取底层限速器实例（供状态查询 API 使用）。"""
        return self._limiter
