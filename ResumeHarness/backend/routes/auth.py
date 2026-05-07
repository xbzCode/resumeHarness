"""用户认证 API：注册、登录、Token 刷新、个人信息。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.middleware.auth import (
    create_jwt,
    hash_password_async,
    verify_jwt,
    verify_password_async,
)
from resume_agent.config.settings import get_settings
from resume_agent.db import get_db
from resume_agent.memory.paths import ensure_user_dirs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Refresh Token 过期时间
_REFRESH_EXPIRE_SECONDS = 3600 * 24 * 30  # 30 天


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(
        min_length=3, max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="用户名（3-32 位，仅字母数字下划线连字符）",
    )
    password: str = Field(min_length=6, max_length=128, description="密码（6-128 位）")
    email: str = Field(default="", max_length=128, description="邮箱（可选）")


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class RefreshRequest(BaseModel):
    """刷新 Token 请求。"""

    refresh_token: str = Field(description="刷新令牌")


class AuthResponse(BaseModel):
    """认证响应。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class ProfileResponse(BaseModel):
    """用户信息响应。"""

    user_id: str
    username: str
    email: str
    created_at: float


class ChangePasswordRequest(BaseModel):
    """修改密码请求。"""

    old_password: str = Field(description="当前密码")
    new_password: str = Field(min_length=6, max_length=128, description="新密码（6-128 位）")


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest) -> Any:
    """用户注册。

    创建用户后自动初始化用户目录，返回 access_token 和 refresh_token。
    """
    db = await get_db()

    # 检查用户名是否已存在
    existing = await db.get_user_by_username(body.username)
    if existing is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    # 密码哈希
    password_hash = await hash_password_async(body.password)

    # 创建用户
    try:
        user_id = await db.create_user(
            username=body.username,
            password_hash=password_hash,
            email=body.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # 初始化用户目录
    ensure_user_dirs(user_id)

    # 生成 Token
    access_token = create_jwt(user_id=user_id, username=body.username)
    refresh_token = create_jwt(
        user_id=user_id,
        username=body.username,
        expire_seconds=_REFRESH_EXPIRE_SECONDS,
    )

    logger.info("用户注册成功: user_id=%s username=%s", user_id, body.username)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        username=body.username,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> Any:
    """用户登录。

    验证用户名密码，返回 access_token 和 refresh_token。
    """
    db = await get_db()

    user = await db.get_user_by_username(body.username)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not await verify_password_async(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 确保 user_id 对应的用户目录存在
    ensure_user_dirs(user["user_id"])

    # 生成 Token
    access_token = create_jwt(
        user_id=user["user_id"], username=user["username"]
    )
    refresh_token = create_jwt(
        user_id=user["user_id"],
        username=user["username"],
        expire_seconds=_REFRESH_EXPIRE_SECONDS,
    )

    logger.info("用户登录: user_id=%s username=%s", user["user_id"], user["username"])

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user["user_id"],
        username=user["username"],
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(body: RefreshRequest) -> Any:
    """刷新 Token。

    使用 refresh_token 获取新的 access_token。
    """
    from resume_agent.exceptions import AuthenticationError, TokenExpiredError

    try:
        payload = verify_jwt(body.refresh_token)
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="刷新令牌已过期，请重新登录")
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="刷新令牌无效")

    user_id = payload["user_id"]
    username = payload.get("username", "")

    # 验证用户仍存在
    db = await get_db()
    user = await db.get_user_by_user_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 生成新 Token
    access_token = create_jwt(user_id=user_id, username=user["username"])
    refresh_token = create_jwt(
        user_id=user_id,
        username=user["username"],
        expire_seconds=_REFRESH_EXPIRE_SECONDS,
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        username=user["username"],
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(request: Request) -> Any:
    """获取当前用户信息。

    需要携带有效的 JWT Token。
    """
    user_id = request.state.user_id
    db = await get_db()

    user = await db.get_user_by_user_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    return ProfileResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user.get("email", ""),
        created_at=user["created_at"],
    )


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request) -> dict[str, Any]:
    """修改密码。需要 JWT 认证。"""
    user_id = request.state.user_id
    db = await get_db()

    user = await db.get_user_by_user_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not await verify_password_async(body.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")

    new_hash = await hash_password_async(body.new_password)
    await db.update_user_password(user_id, new_hash)

    logger.info("用户修改密码: user_id=%s", user_id)
    return {"message": "密码修改成功"}
