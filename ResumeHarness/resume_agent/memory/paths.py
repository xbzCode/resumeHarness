"""用户记忆目录路径管理。"""

from __future__ import annotations

from pathlib import Path

from resume_agent.config.settings import get_settings


def get_user_memory_dir(user_id: str | None = None) -> Path:
    """获取用户记忆目录。"""
    settings = get_settings()
    return settings.get_user_memory_dir(user_id)


def ensure_user_dirs(user_id: str | None = None) -> Path:
    """确保用户目录结构完整，返回用户根目录。"""
    settings = get_settings()
    user_dir = settings.get_user_dir(user_id)

    # 创建所有子目录
    (user_dir / "memory").mkdir(parents=True, exist_ok=True)
    (user_dir / "sessions").mkdir(parents=True, exist_ok=True)
    (user_dir / "resumes").mkdir(parents=True, exist_ok=True)

    return user_dir
