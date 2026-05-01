"""SQLite 数据库管理，P2 阶段替代文件存储。

存储内容：
- 用户认证数据（密码哈希、邮箱等）
- 会话元数据（索引，快照文件仍存磁盘）
- 简历快照索引（文件仍存磁盘）
- IM 渠道映射（channel:sender_id → user_id）
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from resume_agent.config.settings import get_settings

log = logging.getLogger(__name__)


class ResumeAgentDB:
    """SQLite 数据库管理。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            settings = get_settings()
            db_path = settings.data_root / "data.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """建立数据库连接并初始化表结构。"""
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
        log.info("SQLite 数据库已连接: %s", self._db_path)

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            log.info("SQLite 数据库连接已关闭")

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        if self._conn is None:
            self.connect()
        assert self._conn is not None
        return self._conn

    def _create_tables(self) -> None:
        """创建数据表。"""
        cur = self.conn.cursor()

        # 用户表
        cur.execute("""
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
        cur.execute("""
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
        cur.execute("""
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resume_index (
                resume_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                size_bytes  INTEGER DEFAULT 0,
                created_at  REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # 索引
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_meta_user "
            "ON session_meta(user_id, updated_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_resume_index_user "
            "ON resume_index(user_id, created_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_channel_bindings_lookup "
            "ON channel_bindings(channel, sender_id)"
        )

        self.conn.commit()

    # -----------------------------------------------------------------------
    # 用户认证数据
    # -----------------------------------------------------------------------

    def create_user(
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
            self.conn.execute(
                "INSERT INTO users (user_id, username, password_hash, email, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, password_hash, email, now, now),
            )
            self.conn.commit()
            log.info("创建用户: user_id=%s username=%s", user_id, username)
            return user_id
        except sqlite3.IntegrityError as exc:
            if "username" in str(exc):
                raise ValueError(f"用户名已存在: {username}") from exc
            raise

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """按用户名查找用户。"""
        cur = self.conn.execute(
            "SELECT user_id, username, password_hash, email, created_at, updated_at "
            "FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_user_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        """按 user_id 查找用户。"""
        cur = self.conn.execute(
            "SELECT user_id, username, password_hash, email, created_at, updated_at "
            "FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def update_user_password(self, user_id: str, password_hash: str) -> None:
        """更新用户密码。"""
        now = time.time()
        self.conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
            (password_hash, now, user_id),
        )
        self.conn.commit()

    # -----------------------------------------------------------------------
    # IM 渠道映射
    # -----------------------------------------------------------------------

    def bind_channel(self, *, channel: str, sender_id: str, user_id: str) -> None:
        """绑定渠道 sender_id 到 user_id。"""
        now = time.time()
        try:
            self.conn.execute(
                "INSERT INTO channel_bindings (channel, sender_id, user_id, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(channel, sender_id) DO UPDATE SET user_id = excluded.user_id",
                (channel, sender_id, user_id, now),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"渠道绑定失败: {exc}") from exc

    def get_user_by_channel_sender(self, channel: str, sender_id: str) -> dict[str, Any] | None:
        """通过渠道 + sender_id 查找关联的用户。"""
        cur = self.conn.execute(
            "SELECT u.user_id, u.username, u.email, u.created_at "
            "FROM users u "
            "JOIN channel_bindings cb ON u.user_id = cb.user_id "
            "WHERE cb.channel = ? AND cb.sender_id = ?",
            (channel, sender_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    # -----------------------------------------------------------------------
    # 会话元数据
    # -----------------------------------------------------------------------

    def save_session_meta(
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
        self.conn.execute(
            "INSERT INTO session_meta "
            "(user_id, session_id, channel, model, message_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, session_id) DO UPDATE SET "
            "model = excluded.model, "
            "message_count = excluded.message_count, "
            "updated_at = excluded.updated_at",
            (user_id, session_id, channel, model, message_count, now, now),
        )
        self.conn.commit()

    def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的会话。"""
        cur = self.conn.execute(
            "SELECT session_id, channel, model, message_count, created_at, updated_at "
            "FROM session_meta WHERE user_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def delete_session_meta(self, user_id: str, session_id: str) -> bool:
        """删除会话元数据。"""
        cur = self.conn.execute(
            "DELETE FROM session_meta WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # 简历快照索引
    # -----------------------------------------------------------------------

    def save_resume_index(
        self,
        *,
        user_id: str,
        resume_id: str,
        file_path: str,
        size_bytes: int = 0,
    ) -> None:
        """保存简历快照索引。"""
        now = time.time()
        self.conn.execute(
            "INSERT OR REPLACE INTO resume_index (resume_id, user_id, file_path, size_bytes, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (resume_id, user_id, file_path, size_bytes, now),
        )
        self.conn.commit()

    def list_resumes(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的简历快照索引。"""
        cur = self.conn.execute(
            "SELECT resume_id, file_path, size_bytes, created_at "
            "FROM resume_index WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_resume_path(self, resume_id: str) -> str | None:
        """获取简历快照文件路径。"""
        cur = self.conn.execute(
            "SELECT file_path FROM resume_index WHERE resume_id = ?",
            (resume_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return row["file_path"]

    def delete_resume_index(self, resume_id: str) -> bool:
        """删除简历快照索引。"""
        cur = self.conn.execute(
            "DELETE FROM resume_index WHERE resume_id = ?",
            (resume_id,),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_user_resumes(self, user_id: str) -> int:
        """删除用户所有简历索引，返回删除数量。"""
        cur = self.conn.execute(
            "DELETE FROM resume_index WHERE user_id = ?",
            (user_id,),
        )
        self.conn.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# 进程级单例
# ---------------------------------------------------------------------------

_db_instance: ResumeAgentDB | None = None


def get_db() -> ResumeAgentDB:
    """获取数据库实例（懒加载）。"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ResumeAgentDB()
        _db_instance.connect()
    return _db_instance


def close_db() -> None:
    """关闭数据库实例。"""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None
