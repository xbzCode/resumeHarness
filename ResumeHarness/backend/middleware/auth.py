"""JWT 认证中间件。

所有 /api/* 端点（除 /api/auth/* 外）都需要携带有效的 JWT Token。
中间件验证 Token 后将 user_id 注入 request.state.user_id。
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from resume_agent.exceptions import AuthenticationError, TokenExpiredError

logger = logging.getLogger(__name__)

# 不需要认证的路径前缀
_PUBLIC_PATH_PREFIXES = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/share/",     # 公开分享链接（UUID 随机，无需登录）
    "/docs",
    "/openapi.json",
    "/redoc",
)


class AuthMiddleware:
    """JWT 认证中间件（纯 ASGI 实现，避免 BaseHTTPMiddleware 的 body 消费问题）。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 从 scope 中获取路径和方法
        path = scope.get("path", "")
        method = scope.get("method", "")

        # 非 API 路径直接放行
        if not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        # 公开路径放行
        for prefix in _PUBLIC_PATH_PREFIXES:
            if path.startswith(prefix):
                await self.app(scope, receive, send)
                return

        # OPTIONS 请求放行（CORS preflight）
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # 从 headers 中提取 Authorization
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("latin-1")

        if not auth_header.startswith("Bearer "):
            await self._send_auth_error(send, "用户未认证", 1001)
            return

        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        if not token:
            await self._send_auth_error(send, "用户未认证", 1001)
            return

        # 验证 Token
        try:
            payload = verify_jwt(token)
        except TokenExpiredError:
            await self._send_auth_error(send, "Token 过期", 1002)
            return
        except AuthenticationError:
            await self._send_auth_error(send, "Token 无效", 1001)
            return

        # 注入 user_id 到 scope["state"]
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["user_id"] = payload["user_id"]
        scope["state"]["username"] = payload.get("username", "")

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_auth_error(send: Send, detail: str, code: int) -> None:
        """发送认证错误响应。"""
        import json

        body = json.dumps({"detail": detail, "code": code}, ensure_ascii=False).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })


# ---------------------------------------------------------------------------
# JWT 工具函数
# ---------------------------------------------------------------------------

_JWT_SECRET: str | None = None
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_SECONDS = 3600 * 24 * 7  # 7 天
_JWT_REFRESH_EXPIRE_SECONDS = 3600 * 24 * 30  # 30 天


def _get_jwt_secret() -> str:
    """获取或生成 JWT 签名密钥。"""
    global _JWT_SECRET
    if _JWT_SECRET is not None:
        return _JWT_SECRET

    import os
    from pathlib import Path

    from resume_agent.config.settings import get_settings

    settings = get_settings()
    cred_dir = settings.data_root / "credentials"
    cred_dir.mkdir(parents=True, exist_ok=True)

    secret_path = cred_dir / "jwt_secret.key"

    if secret_path.exists():
        _JWT_SECRET = secret_path.read_text(encoding="utf-8").strip()
    else:
        _JWT_SECRET = uuid_hex(32)
        secret_path.write_text(_JWT_SECRET, encoding="utf-8")
        logger.info("生成新的 JWT 密钥: %s", secret_path)

    return _JWT_SECRET


def uuid_hex(length: int = 16) -> str:
    """生成指定长度的随机十六进制字符串。"""
    import uuid
    return uuid.uuid4().hex[:length]


def create_jwt(
    *,
    user_id: str,
    username: str,
    expire_seconds: int | None = None,
) -> str:
    """创建 JWT Token。"""
    import hashlib
    import hmac
    import json
    import time as _time

    secret = _get_jwt_secret()
    exp = expire_seconds or _JWT_EXPIRE_SECONDS

    header = {"alg": _JWT_ALGORITHM, "typ": "JWT"}
    now = _time.time()
    payload = {
        "user_id": user_id,
        "username": username,
        "iat": int(now),
        "exp": int(now + exp),
    }

    # Base64url 编码
    def b64url(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = b64url(signature)

    return f"{signing_input}.{signature_b64}"


def verify_jwt(token: str) -> dict[str, Any]:
    """验证 JWT Token，返回 payload。"""
    import hashlib
    import hmac
    import json
    import time as _time

    import base64

    secret = _get_jwt_secret()

    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Token 格式无效")

    header_b64, payload_b64, signature_b64 = parts

    # 验签
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()

    # Base64url 解码签名（补齐 padding）
    sig_padding = 4 - len(signature_b64) % 4
    if sig_padding != 4:
        signature_b64_padded = signature_b64 + "=" * sig_padding
    else:
        signature_b64_padded = signature_b64

    try:
        actual_sig = base64.urlsafe_b64decode(signature_b64_padded)
    except Exception:
        raise AuthenticationError("Token 签名无效")

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise AuthenticationError("Token 签名无效")

    # 解码 payload
    payload_padding = 4 - len(payload_b64) % 4
    if payload_padding != 4:
        payload_b64_padded = payload_b64 + "=" * payload_padding
    else:
        payload_b64_padded = payload_b64

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64_padded)
        payload = json.loads(payload_json)
    except Exception:
        raise AuthenticationError("Token 载荷无效")

    # 检查过期
    now = _time.time()
    if payload.get("exp", 0) < now:
        raise TokenExpiredError("Token 过期")

    return payload


def hash_password(password: str) -> str:
    """对密码进行哈希。"""
    import hashlib
    import secrets

    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()
    return f"{salt}:{hashed}"


async def hash_password_async(password: str) -> str:
    """异步密码哈希（在线程池中执行 CPU 密集操作）。"""
    import asyncio
    return await asyncio.to_thread(hash_password, password)


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码。"""
    import hashlib

    parts = password_hash.split(":", 1)
    if len(parts) != 2:
        return False

    salt, stored_hash = parts
    computed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()
    return computed == stored_hash


async def verify_password_async(password: str, password_hash: str) -> bool:
    """异步密码验证（在线程池中执行 CPU 密集操作）。"""
    import asyncio
    return await asyncio.to_thread(verify_password, password, password_hash)
