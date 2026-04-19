"""用户配置 API。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from resume_agent.config.settings import (
    UserSettings,
    get_settings,
    load_user_settings,
    save_user_settings,
)
from resume_agent.memory.paths import ensure_user_dirs

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


def _get_user_id(request: Request) -> str:
    """获取当前用户 ID（P1 开发模式使用默认值）。"""
    settings = get_settings()
    return settings.effective_default_user_id


@router.get("/settings")
async def get_user_settings_api(request: Request) -> dict[str, Any]:
    """获取当前用户配置。"""
    user_id = _get_user_id(request)
    ensure_user_dirs(user_id)
    user_settings = load_user_settings(user_id)
    return user_settings.model_dump()


@router.put("/settings")
async def update_user_settings_api(
    request: Request,
    body: dict[str, Any],
) -> dict[str, Any]:
    """更新当前用户配置。

    Body 可包含 UserSettings 的任意字段，未提供的字段保持原值。
    """
    user_id = _get_user_id(request)

    # 加载当前配置
    current = load_user_settings(user_id)

    # 合并更新
    update_data = {}
    for key in UserSettings.model_fields:
        if key in body:
            update_data[key] = body[key]

    if update_data:
        updated = current.model_copy(update=update_data)
    else:
        updated = current

    # 保存
    path = save_user_settings(user_id, updated)
    logger.info("更新用户配置: user=%s path=%s", user_id, path)

    return updated.model_dump()
