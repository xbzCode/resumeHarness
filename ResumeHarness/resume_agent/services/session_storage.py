"""会话快照持久化。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from resume_agent.api.usage import UsageSnapshot
from resume_agent.engine.messages import ConversationMessage

from resume_agent.config.settings import get_settings


def save_session_snapshot(
    *,
    user_id: str,
    model: str,
    system_prompt: str,
    messages: list[ConversationMessage],
    usage: UsageSnapshot,
    session_id: str | None = None,
    tool_metadata: dict[str, object] | None = None,
) -> Path:
    """持久化会话快照。"""
    settings = get_settings()
    sessions_dir = settings.get_user_sessions_dir(user_id)
    sid = session_id or uuid4().hex[:12]

    summary = ""
    for msg in messages:
        if msg.role == "user" and msg.text.strip():
            summary = msg.text.strip()[:80]
            break

    payload = {
        "app": "resume-agent",
        "session_id": sid,
        "user_id": user_id,
        "model": model,
        "system_prompt": system_prompt,
        "messages": [message.model_dump(mode="json") for message in messages],
        "usage": usage.model_dump(),
        "created_at": time.time(),
        "summary": summary,
        "message_count": len(messages),
    }
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    # 保存为 latest 和按 ID 保存
    latest_path = sessions_dir / "latest.json"
    latest_path.write_text(data, encoding="utf-8")

    session_path = sessions_dir / f"session-{sid}.json"
    session_path.write_text(data, encoding="utf-8")

    # 同步元数据到 SQLite
    _sync_session_meta_to_db(
        user_id=user_id,
        session_id=sid,
        model=model,
        message_count=len(messages),
        summary=summary,
    )

    return latest_path


def load_latest_snapshot(user_id: str) -> dict[str, Any] | None:
    """加载最近的会话快照。"""
    settings = get_settings()
    path = settings.get_user_sessions_dir(user_id) / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_session_snapshots(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """列出用户的会话快照。"""
    settings = get_settings()
    sessions_dir = settings.get_user_sessions_dir(user_id)
    sessions: list[dict[str, Any]] = []

    for path in sorted(
        sessions_dir.glob("session-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append({
                "session_id": data.get("session_id", path.stem.replace("session-", "")),
                "summary": data.get("summary", ""),
                "message_count": data.get("message_count", 0),
                "model": data.get("model", ""),
                "created_at": data.get("created_at", path.stat().st_mtime),
            })
        except (json.JSONDecodeError, OSError):
            continue
        if len(sessions) >= limit:
            break

    return sessions


def _sync_session_meta_to_db(
    *,
    user_id: str,
    session_id: str,
    model: str,
    message_count: int,
    summary: str = "",
) -> None:
    """同步会话元数据到 SQLite 数据库。"""
    try:
        from resume_agent.db import get_db

        db = get_db()
        db.save_session_meta(
            user_id=user_id,
            session_id=session_id,
            channel="web",
            model=model,
            message_count=message_count,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "同步会话元数据到 SQLite 失败: %s", exc
        )
