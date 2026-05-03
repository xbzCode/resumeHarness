"""用户级 API 速率限制器。

按 user_id 维护令牌桶，防止单用户过度消耗 API 配额。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from resume_agent.exceptions import RateLimitError

log = logging.getLogger(__name__)


@dataclass
class UserBucket:
    """单用户的令牌桶。"""

    user_id: str
    rpm: int  # 每分钟允许的请求数
    _tokens: float = 0.0
    _last_refill: float = field(default_factory=time.monotonic)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _refill(self) -> None:
        """补充令牌。"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        # 按时间比例补充令牌
        new_tokens = elapsed * (self.rpm / 60.0)
        self._tokens = min(self.rpm, self._tokens + new_tokens)
        self._last_refill = now

    async def acquire(self) -> None:
        """获取一个令牌，无可用令牌时等待。"""
        async with self._lock:
            self._refill()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

        # 等待令牌补充
        wait_time = (1.0 - self._tokens) / (self.rpm / 60.0)
        await asyncio.sleep(wait_time)

        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
            else:
                # 极端情况下仍无法获取
                self._tokens = max(0, self._tokens - 1.0)

    def try_acquire(self) -> bool:
        """尝试获取令牌（非阻塞）。

        Returns:
            是否成功获取
        """
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


class UserRateLimiter:
    """用户级 API 速率限制器。

    按 user_id 维护独立的令牌桶，限制每用户的请求频率。

    用法：
        limiter = UserRateLimiter(rpm=20)
        await limiter.acquire("user_123")  # 阻塞等待
        # 或
        if limiter.try_acquire("user_123"):  # 非阻塞
            # 执行请求
    """

    def __init__(self, rpm: int = 20, max_users: int = 100) -> None:
        self._rpm = rpm
        self._max_users = max_users
        self._buckets: dict[str, UserBucket] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: str) -> None:
        """获取令牌（阻塞等待）。

        Args:
            user_id: 用户 ID

        Raises:
            RateLimitError: 超过最大等待时间
        """
        bucket = await self._get_bucket(user_id)
        await bucket.acquire()

    def try_acquire(self, user_id: str) -> bool:
        """尝试获取令牌（非阻塞）。

        Args:
            user_id: 用户 ID

        Returns:
            是否成功获取
        """
        bucket = self._buckets.get(user_id)
        if bucket is None:
            # 新用户，直接创建并允许
            bucket = UserBucket(user_id=user_id, rpm=self._rpm)
            bucket._tokens = self._rpm - 1  # 消耗一个令牌
            self._buckets[user_id] = bucket
            return True
        return bucket.try_acquire()

    async def _get_bucket(self, user_id: str) -> UserBucket:
        """获取或创建用户令牌桶。"""
        if user_id in self._buckets:
            return self._buckets[user_id]

        async with self._lock:
            if user_id in self._buckets:
                return self._buckets[user_id]

            # 清理超出限制的旧桶
            if len(self._buckets) >= self._max_users:
                self._cleanup_old_buckets()

            bucket = UserBucket(user_id=user_id, rpm=self._rpm)
            self._buckets[user_id] = bucket
            return bucket

    def _cleanup_old_buckets(self) -> None:
        """清理最旧的令牌桶。"""
        if not self._buckets:
            return

        # 移除最旧的一半桶（简化策略）
        sorted_buckets = sorted(
            self._buckets.items(),
            key=lambda x: x[1]._last_refill,
        )
        to_remove = len(sorted_buckets) // 2
        for user_id, _ in sorted_buckets[:to_remove]:
            del self._buckets[user_id]

    def get_status(self, user_id: str) -> dict:
        """获取用户的速率限制状态。"""
        bucket = self._buckets.get(user_id)
        if bucket is None:
            return {
                "user_id": user_id,
                "rpm_limit": self._rpm,
                "tokens_available": self._rpm,
                "limited": False,
            }

        bucket._refill()
        return {
            "user_id": user_id,
            "rpm_limit": self._rpm,
            "tokens_available": round(bucket._tokens, 1),
            "limited": bucket._tokens < 1.0,
        }
