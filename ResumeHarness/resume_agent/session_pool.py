"""多租户会话池，LRU 淘汰空闲会话。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from resume_agent.engine.messages import ConversationMessage
from resume_agent.runtime import RuntimeBundle, build_resume_runtime
from resume_agent.services.session_storage import load_session_snapshot, save_session_snapshot

log = logging.getLogger(__name__)


@dataclass
class SessionEntry:
    """会话条目。"""

    bundle: RuntimeBundle
    last_access: float
    session_key: str


class ResumeSessionPool:
    """管理多用户并发会话，LRU 淘汰空闲会话。"""

    def __init__(self, max_sessions: int = 20, idle_timeout: int = 1800) -> None:
        self._entries: dict[str, SessionEntry] = {}  # session_key → entry
        self._max_sessions = max_sessions
        self._idle_timeout = idle_timeout
        self._lock = asyncio.Lock()
        self._eviction_task: asyncio.Task | None = None

    @staticmethod
    def make_session_key(channel: str, user_id: str, session_id: str | None = None) -> str:
        """构造会话 Key。"""
        return f"{channel}:{user_id}:{session_id or 'default'}"

    async def start(self) -> None:
        """启动定时淘汰任务。"""
        if self._eviction_task is None:
            self._eviction_task = asyncio.create_task(self._eviction_loop())

    async def stop(self) -> None:
        """停止定时淘汰任务并清理所有会话。"""
        if self._eviction_task is not None:
            self._eviction_task.cancel()
            try:
                await self._eviction_task
            except asyncio.CancelledError:
                pass
            self._eviction_task = None

        # 保存所有会话快照
        for key, entry in list(self._entries.items()):
            try:
                await self._save_snapshot(entry)
            except Exception as exc:
                log.warning("保存会话快照失败 %s: %s", key, exc)

        self._entries.clear()

    async def get_or_create(
        self,
        user_id: str,
        session_id: str | None = None,
        *,
        channel: str = "web",
        model: str | None = None,
        system_prompt: str | None = None,
        latest_user_prompt: str | None = None,
    ) -> RuntimeBundle:
        """获取已有会话或创建新会话。"""
        session_key = self.make_session_key(channel, user_id, session_id)

        async with self._lock:
            if session_key in self._entries:
                entry = self._entries[session_key]
                entry.last_access = time.monotonic()
                return entry.bundle

            # 淘汰超限会话
            if len(self._entries) >= self._max_sessions:
                await self._evict_oldest()

            # 创建新会话
            bundle = await build_resume_runtime(
                user_id=user_id,
                session_id=session_id,
                model=model,
                system_prompt=system_prompt,
                latest_user_prompt=latest_user_prompt,
            )

            # 尝试从磁盘快照恢复历史消息
            if session_id:
                await self._restore_history(bundle, user_id, session_id)

            self._entries[session_key] = SessionEntry(
                bundle=bundle,
                last_access=time.monotonic(),
                session_key=session_key,
            )

            log.info("创建新会话: %s (user=%s)", session_key, user_id)
            return bundle

    async def release(self, session_key: str) -> None:
        """标记会话空闲，不立即销毁。"""
        if session_key in self._entries:
            self._entries[session_key].last_access = time.monotonic()

    async def remove(self, session_key: str) -> None:
        """立即移除指定会话。"""
        async with self._lock:
            entry = self._entries.pop(session_key, None)
            if entry:
                try:
                    await self._save_snapshot(entry)
                except Exception as exc:
                    log.warning("保存会话快照失败 %s: %s", session_key, exc)
                log.info("移除会话: %s", session_key)

    async def evict_idle(self) -> int:
        """淘汰超时空闲会话，返回淘汰数量。"""
        now = time.monotonic()
        evicted = 0

        async with self._lock:
            expired_keys = [
                key
                for key, entry in self._entries.items()
                if now - entry.last_access > self._idle_timeout
            ]

            for key in expired_keys:
                entry = self._entries.pop(key)
                try:
                    await self._save_snapshot(entry)
                except Exception as exc:
                    log.warning("保存会话快照失败 %s: %s", key, exc)
                evicted += 1
                log.info("淘汰空闲会话: %s", key)

        return evicted

    def list_active_sessions(self) -> list[dict]:
        """列出所有活跃会话。"""
        now = time.monotonic()
        return [
            {
                "session_key": entry.session_key,
                "user_id": entry.bundle.user_id,
                "session_id": entry.bundle.session_id,
                "model": entry.bundle.model,
                "idle_seconds": int(now - entry.last_access),
            }
            for entry in self._entries.values()
        ]

    async def _evict_oldest(self) -> None:
        """淘汰最早访问的会话（容量满时强制淘汰）。"""
        if not self._entries:
            return

        oldest_key = min(self._entries, key=lambda k: self._entries[k].last_access)
        entry = self._entries.pop(oldest_key)
        try:
            await self._save_snapshot(entry)
        except Exception as exc:
            log.warning("保存会话快照失败 %s: %s", oldest_key, exc)
        log.info("强制淘汰最旧会话: %s", oldest_key)

    async def _save_snapshot(self, entry: SessionEntry) -> None:
        """保存会话快照到磁盘。"""
        try:
            bundle = entry.bundle
            save_session_snapshot(
                user_id=bundle.user_id,
                model=bundle.model,
                system_prompt=bundle.system_prompt,
                messages=bundle.engine.messages,
                usage=bundle.engine.total_usage,
                session_id=bundle.session_id,
                tool_metadata=bundle.engine.tool_metadata,
            )
            log.debug("保存会话快照: %s", entry.session_key)
        except Exception as exc:
            log.warning("保存会话快照失败 %s: %s", entry.session_key, exc)

    async def _restore_history(
        self, bundle: RuntimeBundle, user_id: str, session_id: str
    ) -> None:
        """从磁盘快照恢复历史消息到 bundle。"""
        try:
            snapshot = load_session_snapshot(user_id, session_id)
            if snapshot is None:
                return
            raw_messages = snapshot.get("messages", [])
            if not raw_messages:
                return
            messages = [ConversationMessage.model_validate(m) for m in raw_messages]
            bundle.engine.load_messages(messages)
            log.info(
                "恢复会话历史: session_id=%s, 消息数=%d", session_id, len(messages)
            )
        except Exception as exc:
            log.warning("恢复会话历史失败 session_id=%s: %s", session_id, exc)

    async def _eviction_loop(self) -> None:
        """定时淘汰循环（每 5 分钟）。"""
        try:
            while True:
                await asyncio.sleep(300)  # 5 分钟
                count = await self.evict_idle()
                if count > 0:
                    log.info("定时淘汰完成，淘汰 %d 个空闲会话", count)
        except asyncio.CancelledError:
            pass
