"""SQLite 数据库管理（异步版本，使用 aiosqlite）。

存储内容：
- 用户认证数据（密码哈希、邮箱等）
- 会话元数据（索引，快照文件仍存磁盘）
- 简历快照索引（文件仍存磁盘）
- IM 渠道映射（channel:sender_id → user_id）
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from resume_agent.config.settings import get_settings

log = logging.getLogger(__name__)


class ResumeAgentDB:
    """异步 SQLite 数据库管理。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            settings = get_settings()
            db_path = settings.data_root / "data.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """建立数据库连接并初始化表结构。"""
        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        log.info("SQLite 数据库已连接: %s", self._db_path)

    async def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            log.info("SQLite 数据库连接已关闭")

    @property
    def conn(self) -> aiosqlite.Connection:
        """获取数据库连接。"""
        if self._conn is None:
            raise RuntimeError("数据库未连接，请先调用 await db.connect()")
        return self._conn

    async def _create_tables(self) -> None:
        """创建数据表。"""
        # 用户表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT PRIMARY KEY,
                username    TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email       TEXT DEFAULT '',
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            )
        """)

        # IM 渠道映射表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_bindings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                channel     TEXT NOT NULL,
                sender_id   TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                created_at  REAL NOT NULL,
                UNIQUE(channel, sender_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # 会话元数据表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_meta (
                user_id     TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                channel     TEXT DEFAULT 'web',
                model       TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL,
                PRIMARY KEY (user_id, session_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # 简历快照索引表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS resume_index (
                resume_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                size_bytes  INTEGER DEFAULT 0,
                created_at  REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # 简历分享链接表
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS share_links (
                share_id    TEXT PRIMARY KEY,
                resume_id   TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                template    TEXT DEFAULT 'professional',
                created_at  REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # 索引
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_meta_user "
            "ON session_meta(user_id, updated_at DESC)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resume_index_user "
            "ON resume_index(user_id, created_at DESC)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_channel_bindings_lookup "
            "ON channel_bindings(channel, sender_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_share_links_resume "
            "ON share_links(resume_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_share_links_user "
            "ON share_links(user_id, created_at DESC)"
        )

        await self.conn.commit()

    # -----------------------------------------------------------------------
    # 用户认证数据
    # -----------------------------------------------------------------------

    async def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        email: str = "",
    ) -> str:
        """创建用户，返回 user_id。"""
        user_id = uuid.uuid4().hex[:16]
        now = time.time()

        try:
            await self.conn.execute(
                "INSERT INTO users (user_id, username, password_hash, email, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, password_hash, email, now, now),
            )
            await self.conn.commit()
            log.info("创建用户: user_id=%s username=%s", user_id, username)
            return user_id
        except aiosqlite.IntegrityError as exc:
            if "username" in str(exc):
                raise ValueError(f"用户名已存在: {username}") from exc
            raise

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """按用户名查找用户。"""
        cur = await self.conn.execute(
            "SELECT user_id, username, password_hash, email, created_at, updated_at "
            "FROM users WHERE username = ?",
            (username,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_user_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        """按 user_id 查找用户。"""
        cur = await self.conn.execute(
            "SELECT user_id, username, password_hash, email, created_at, updated_at "
            "FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    async def update_user_password(self, user_id: str, password_hash: str) -> None:
        """更新用户密码。"""
        now = time.time()
        await self.conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
            (password_hash, now, user_id),
        )
        await self.conn.commit()

    # -----------------------------------------------------------------------
    # IM 渠道映射
    # -----------------------------------------------------------------------

    async def bind_channel(self, *, channel: str, sender_id: str, user_id: str) -> None:
        """绑定渠道 sender_id 到 user_id。"""
        now = time.time()
        try:
            await self.conn.execute(
                "INSERT INTO channel_bindings (channel, sender_id, user_id, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(channel, sender_id) DO UPDATE SET user_id = excluded.user_id",
                (channel, sender_id, user_id, now),
            )
            await self.conn.commit()
        except aiosqlite.IntegrityError as exc:
            raise ValueError(f"渠道绑定失败: {exc}") from exc

    async def get_user_by_channel_sender(self, channel: str, sender_id: str) -> dict[str, Any] | None:
        """通过渠道 + sender_id 查找关联的用户。"""
        cur = await self.conn.execute(
            "SELECT u.user_id, u.username, u.email, u.created_at "
            "FROM users u "
            "JOIN channel_bindings cb ON u.user_id = cb.user_id "
            "WHERE cb.channel = ? AND cb.sender_id = ?",
            (channel, sender_id),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    # -----------------------------------------------------------------------
    # 会话元数据
    # -----------------------------------------------------------------------

    async def save_session_meta(
        self,
        *,
        user_id: str,
        session_id: str,
        channel: str = "web",
        model: str = "",
        message_count: int = 0,
    ) -> None:
        """保存/更新会话元数据。"""
        now = time.time()
        await self.conn.execute(
            "INSERT INTO session_meta "
            "(user_id, session_id, channel, model, message_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, session_id) DO UPDATE SET "
            "model = excluded.model, "
            "message_count = excluded.message_count, "
            "updated_at = excluded.updated_at",
            (user_id, session_id, channel, model, message_count, now, now),
        )
        await self.conn.commit()

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的会话。"""
        cur = await self.conn.execute(
            "SELECT session_id, channel, model, message_count, created_at, updated_at "
            "FROM session_meta WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def delete_session_meta(self, user_id: str, session_id: str) -> bool:
        """删除会话元数据。"""
        cur = await self.conn.execute(
            "DELETE FROM session_meta WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # 简历快照索引
    # -----------------------------------------------------------------------

    async def save_resume_index(
        self,
        *,
        user_id: str,
        resume_id: str,
        file_path: str,
        size_bytes: int = 0,
    ) -> None:
        """保存简历快照索引。"""
        now = time.time()
        await self.conn.execute(
            "INSERT OR REPLACE INTO resume_index (resume_id, user_id, file_path, size_bytes, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (resume_id, user_id, file_path, size_bytes, now),
        )
        await self.conn.commit()

    async def list_resumes(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的简历快照索引。"""
        cur = await self.conn.execute(
            "SELECT resume_id, file_path, size_bytes, created_at "
            "FROM resume_index WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]

    async def get_resume_path(self, resume_id: str) -> str | None:
        """获取简历快照文件路径。"""
        cur = await self.conn.execute(
            "SELECT file_path FROM resume_index WHERE resume_id = ?",
            (resume_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return row["file_path"]

    async def delete_resume_index(self, resume_id: str) -> bool:
        """删除简历快照索引。"""
        cur = await self.conn.execute(
            "DELETE FROM resume_index WHERE resume_id = ?",
            (resume_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def delete_user_resumes(self, user_id: str) -> int:
        """删除用户所有简历索引，返回删除数量。"""
        cur = await self.conn.execute(
            "DELETE FROM resume_index WHERE user_id = ?",
            (user_id,),
        )
        await self.conn.commit()
        return cur.rowcount

    # -----------------------------------------------------------------------
    # 分享链接
    # -----------------------------------------------------------------------

    async def create_share_link(
        self,
        *,
        resume_id: str,
        user_id: str,
        template: str = "professional",
    ) -> str:
        """创建简历分享链接，返回 share_id（UUID）。
        
        如果该简历已有分享链接，则重新生成（旧的作废）。
        """
        # 删除旧的分享链接
        await self.conn.execute(
            "DELETE FROM share_links WHERE resume_id = ? AND user_id = ?",
            (resume_id, user_id),
        )

        share_id = str(uuid.uuid4())
        now = time.time()
        await self.conn.execute(
            "INSERT INTO share_links (share_id, resume_id, user_id, template, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (share_id, resume_id, user_id, template, now),
        )
        await self.conn.commit()
        log.info("创建分享链接: share_id=%s resume_id=%s user=%s", share_id, resume_id, user_id)
        return share_id

    async def get_share_link(self, share_id: str) -> dict[str, Any] | None:
        """通过 share_id 查找分享链接。"""
        cur = await self.conn.execute(
            "SELECT share_id, resume_id, user_id, template, created_at "
            "FROM share_links WHERE share_id = ?",
            (share_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_share_link_by_resume(self, user_id: str, resume_id: str) -> dict[str, Any] | None:
        """获取用户某份简历的分享链接。"""
        cur = await self.conn.execute(
            "SELECT share_id, resume_id, user_id, template, created_at "
            "FROM share_links WHERE user_id = ? AND resume_id = ?",
            (user_id, resume_id),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    async def delete_share_link(self, share_id: str) -> bool:
        """删除分享链接。"""
        cur = await self.conn.execute(
            "DELETE FROM share_links WHERE share_id = ?",
            (share_id,),
        )
        await self.conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# 进程级单例
# ---------------------------------------------------------------------------

_db_instance: ResumeAgentDB | None = None


async def get_db() -> ResumeAgentDB:
    """获取数据库实例（懒加载）。"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ResumeAgentDB()
        await _db_instance.connect()
    return _db_instance


async def close_db() -> None:
    """关闭数据库实例。"""
    global _db_instance
    if _db_instance is not None:
        await _db_instance.close()
        _db_instance = None
