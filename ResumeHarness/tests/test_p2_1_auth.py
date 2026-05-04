"""P2-1 验收测试：SQLite 数据库 + JWT 认证 + 认证中间件 + PDF 解析。"""

from __future__ import annotations

import io
import os
import tempfile

import pytest

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-key-for-unit-test")


# ─── SQLite 数据库 ────────────────────────────────────────────


class TestResumeAgentDB:
    """测试 resume_agent.db.ResumeAgentDB。"""

    @pytest.fixture()
    async def db(self, tmp_path):
        from resume_agent.db import ResumeAgentDB

        db_path = tmp_path / "test.db"
        database = ResumeAgentDB(str(db_path))
        await database.connect()
        yield database
        await database.close()

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, db):
        uid = await db.create_user(username="alice", password_hash="hash1")
        assert uid is not None and len(uid) > 0
        user = await db.get_user_by_username("alice")
        assert user is not None
        assert user["username"] == "alice"
        assert user["password_hash"] == "hash1"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db):
        user = await db.get_user_by_username("nonexist")
        assert user is None

    @pytest.mark.asyncio
    async def test_duplicate_username_raises(self, db):
        await db.create_user(username="bob", password_hash="h1")
        with pytest.raises(ValueError, match="用户名已存在"):
            await db.create_user(username="bob", password_hash="h2")

    @pytest.mark.asyncio
    async def test_get_user_by_user_id(self, db):
        uid = await db.create_user(username="charlie", password_hash="h1")
        user = await db.get_user_by_user_id(uid)
        assert user is not None
        assert user["username"] == "charlie"

    @pytest.mark.asyncio
    async def test_update_user_password(self, db):
        uid = await db.create_user(username="dave", password_hash="h1")
        await db.update_user_password(uid, "new_hash")
        user = await db.get_user_by_username("dave")
        assert user["password_hash"] == "new_hash"

    @pytest.mark.asyncio
    async def test_bind_channel(self, db):
        uid = await db.create_user(username="eve", password_hash="h1")
        await db.bind_channel(channel="wechat", sender_id="wx_123", user_id=uid)
        result = await db.get_user_by_channel_sender("wechat", "wx_123")
        assert result is not None
        assert result["user_id"] == uid
        assert result["username"] == "eve"

    @pytest.mark.asyncio
    async def test_bind_channel_upsert(self, db):
        uid1 = await db.create_user(username="frank", password_hash="h1")
        uid2 = await db.create_user(username="grace", password_hash="h2")
        await db.bind_channel(channel="wechat", sender_id="wx_456", user_id=uid1)
        await db.bind_channel(channel="wechat", sender_id="wx_456", user_id=uid2)
        result = await db.get_user_by_channel_sender("wechat", "wx_456")
        assert result["user_id"] == uid2

    @pytest.mark.asyncio
    async def test_save_session_meta(self, db):
        uid = await db.create_user(username="heidi", password_hash="h1")
        await db.save_session_meta(user_id=uid, session_id="sess_1", channel="web", model="deepseek-chat")
        sessions = await db.list_sessions(uid)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess_1"

    @pytest.mark.asyncio
    async def test_delete_session_meta(self, db):
        uid = await db.create_user(username="ivan", password_hash="h1")
        await db.save_session_meta(user_id=uid, session_id="sess_2")
        assert await db.delete_session_meta(uid, "sess_2") is True
        assert await db.delete_session_meta(uid, "nonexist") is False

    @pytest.mark.asyncio
    async def test_save_resume_index(self, db):
        uid = await db.create_user(username="judy", password_hash="h1")
        await db.save_resume_index(user_id=uid, resume_id="res_1", file_path="/path/resume.md", size_bytes=1024)
        resumes = await db.list_resumes(uid)
        assert len(resumes) == 1
        assert resumes[0]["resume_id"] == "res_1"

    @pytest.mark.asyncio
    async def test_get_resume_path(self, db):
        uid = await db.create_user(username="karl", password_hash="h1")
        await db.save_resume_index(user_id=uid, resume_id="res_2", file_path="/path/resume2.md")
        assert await db.get_resume_path("res_2") == "/path/resume2.md"
        assert await db.get_resume_path("nonexist") is None

    @pytest.mark.asyncio
    async def test_delete_resume_index(self, db):
        uid = await db.create_user(username="larry", password_hash="h1")
        await db.save_resume_index(user_id=uid, resume_id="res_3", file_path="/path/resume3.md")
        assert await db.delete_resume_index("res_3") is True
        assert await db.delete_resume_index("nonexist") is False


# ─── JWT 工具函数 ─────────────────────────────────────────────


class TestJWT:
    """测试 backend.middleware.auth 中的 JWT 工具。"""

    def test_create_and_verify_jwt(self):
        from backend.middleware.auth import create_jwt, verify_jwt

        token = create_jwt(user_id="uid_123", username="alice")
        payload = verify_jwt(token)
        assert payload["user_id"] == "uid_123"
        assert payload["username"] == "alice"

    def test_verify_expired_jwt(self):
        from backend.middleware.auth import create_jwt, verify_jwt

        # 创建一个已过期的 token（expire_seconds=1，等待过期）
        token = create_jwt(user_id="uid_123", username="alice", expire_seconds=1)
        import time
        time.sleep(2)
        from resume_agent.exceptions import TokenExpiredError
        with pytest.raises(TokenExpiredError):
            verify_jwt(token)

    def test_verify_invalid_jwt(self):
        from backend.middleware.auth import verify_jwt
        from resume_agent.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            verify_jwt("invalid.token.here")


# ─── 密码哈希 ─────────────────────────────────────────────────


class TestPasswordHash:
    """测试密码哈希与验证。"""

    def test_hash_and_verify(self):
        from backend.middleware.auth import hash_password, verify_password

        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed) is True
        assert verify_password("wrongpassword", hashed) is False


# ─── Auth API 端点 ────────────────────────────────────────────


class TestAuthAPI:
    """测试 backend.routes.auth 路由。"""

    @pytest.fixture()
    async def client(self, tmp_path, monkeypatch):
        from httpx import AsyncClient, ASGITransport
        from resume_agent.db import ResumeAgentDB
        from backend.app import create_app

        db_path = tmp_path / "test_api.db"
        db = ResumeAgentDB(str(db_path))
        await db.connect()

        # 用临时数据库替换全局单例
        import resume_agent.db as db_mod
        monkeypatch.setattr(db_mod, "_db_instance", db)

        # 设置数据目录到临时路径
        monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await db.close()

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "Pass1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["username"] == "testuser"
        assert data["user_id"] is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client):
        await client.post("/api/auth/register", json={"username": "dup", "password": "Pass1234!"})
        resp = await client.post("/api/auth/register", json={"username": "dup", "password": "Pass5678!"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        await client.post("/api/auth/register", json={"username": "loginuser", "password": "Pass1234!"})
        resp = await client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "Pass1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={"username": "wrongpw", "password": "Pass1234!"})
        resp = await client.post(
            "/api/auth/login",
            json={"username": "wrongpw", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client):
        reg = await client.post(
            "/api/auth/register",
            json={"username": "refreshuser", "password": "Pass1234!"},
        )
        refresh_token = reg.json()["refresh_token"]
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_profile_with_auth(self, client):
        reg = await client.post(
            "/api/auth/register",
            json={"username": "profileuser", "password": "Pass1234!"},
        )
        access_token = reg.json()["access_token"]
        resp = await client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "profileuser"

    @pytest.mark.asyncio
    async def test_profile_without_auth(self, client):
        resp = await client.get("/api/auth/profile")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client):
        # /api/settings 应该需要认证
        resp = await client.get("/api/settings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_auth(self, client):
        reg = await client.post(
            "/api/auth/register",
            json={"username": "protected", "password": "Pass1234!"},
        )
        access_token = reg.json()["access_token"]
        resp = await client.get(
            "/api/settings",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200


# ─── PDF 解析 ─────────────────────────────────────────────────


class TestPDFExtraction:
    """测试 PDF 文本提取。"""

    def test_extract_from_simple_pdf(self):
        """创建一个简单的 PDF 并提取文本。"""
        from backend.routes.memory import _extract_pdf_text

        try:
            from fpdf import FPDF
        except ImportError:
            pytest.skip("fpdf not installed")

        # 创建简单 PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(text="Hello World", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(text="This is a test resume", new_x="LMARGIN", new_y="NEXT")

        raw_bytes = pdf.output()
        text = _extract_pdf_text(raw_bytes)
        assert "Hello World" in text
        assert "test resume" in text

    def test_extract_from_empty_pdf(self):
        """空 PDF 应返回空字符串。"""
        from backend.routes.memory import _extract_pdf_text

        try:
            from fpdf import FPDF
        except ImportError:
            pytest.skip("fpdf not installed")

        pdf = FPDF()
        pdf.add_page()
        raw_bytes = pdf.output()
        text = _extract_pdf_text(raw_bytes)
        assert text.strip() == ""
