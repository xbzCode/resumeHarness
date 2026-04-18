"""DeepSeek 多 API Key 轮询池，按 Key 维护令牌桶，公平分配请求。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from resume_agent.exceptions import RateLimitError

log = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """简易令牌桶限流器。"""

    rpm: int  # 每分钟允许的请求数
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        added = elapsed * (self.rpm / 60.0)
        self.tokens = min(self.rpm, self.tokens + added)
        self.last_refill = now

    def try_acquire(self) -> bool:
        """尝试获取一个令牌，非阻塞。"""
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    async def wait_and_acquire(self, timeout: float = 30.0) -> bool:
        """等待直到获取一个令牌，或超时。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.try_acquire():
                return True
            await asyncio.sleep(0.5)
        return False


class ApiKeyPool:
    """API Key 轮询池，按 Key 维护令牌桶，公平分配请求。"""

    def __init__(self, api_keys: list[str], rpm_per_key: int = 30) -> None:
        if not api_keys:
            raise ValueError("api_keys 不能为空")
        self._keys = api_keys
        self._buckets: dict[str, TokenBucket] = {
            key: TokenBucket(rpm=rpm_per_key) for key in api_keys
        }
        self._suspended: dict[str, float] = {}  # key → 恢复时间
        self._index = 0

    @property
    def keys(self) -> list[str]:
        return list(self._keys)

    def _is_suspended(self, key: str) -> bool:
        if key not in self._suspended:
            return False
        if time.monotonic() >= self._suspended[key]:
            del self._suspended[key]
            return False
        return True

    async def acquire(self, timeout: float = 30.0) -> str:
        """获取一个可用的 API Key，若全部达到限额则排队等待。

        使用轮询策略在可用的 Key 之间均匀分配请求。
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            # 尝试轮询获取
            for _ in range(len(self._keys)):
                key = self._keys[self._index % len(self._keys)]
                self._index += 1
                if self._is_suspended(key):
                    continue
                bucket = self._buckets[key]
                if bucket.try_acquire():
                    return key

            # 所有 Key 都暂时不可用，短暂等待后重试
            await asyncio.sleep(0.3)

        raise RateLimitError("所有 API Key 均已达到速率限制，请稍后重试")

    def report_429(self, key: str, suspend_seconds: float = 10.0) -> None:
        """报告某 Key 收到 429，暂时停用该 Key。"""
        self._suspended[key] = time.monotonic() + suspend_seconds
        log.warning("API Key %s*** 收到 429，暂停 %.0f 秒", key[:8], suspend_seconds)

    def get_status(self) -> list[dict]:
        """获取所有 Key 的状态。"""
        result = []
        for key in self._keys:
            bucket = self._buckets[key]
            bucket._refill()
            result.append({
                "key_suffix": key[-4:] if len(key) > 4 else "****",
                "available_tokens": round(bucket.tokens, 1),
                "suspended": self._is_suspended(key),
            })
        return result
