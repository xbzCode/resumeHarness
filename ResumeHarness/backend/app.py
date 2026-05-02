"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.auth import AuthMiddleware
from resume_agent.config.settings import get_settings, validate_api_config
from resume_agent.db import close_db, get_db
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

# 全局会话池
session_pool: ResumeSessionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    global session_pool

    # 启动时校验配置
    try:
        validate_api_config()
        logger.info("API 配置校验通过")
    except Exception as exc:
        logger.error("API 配置校验失败: %s", exc)
        raise

    # 初始化数据库
    db = get_db()
    logger.info("数据库已初始化")

    # 启动会话池
    settings = get_settings()
    session_pool = ResumeSessionPool(
        max_sessions=settings.max_sessions,
        idle_timeout=settings.idle_timeout,
    )
    await session_pool.start()
    logger.info("会话池已启动 (max=%d, idle_timeout=%ds)", settings.max_sessions, settings.idle_timeout)

    yield

    # 关闭会话池
    if session_pool is not None:
        await session_pool.stop()
        logger.info("会话池已关闭")

    # 关闭数据库
    close_db()
    logger.info("数据库已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title="Resume Agent",
        description="简历智能体 Web API",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # JWT 认证中间件（在 CORS 之后添加，这样 CORS preflight 不受影响）
    app.add_middleware(AuthMiddleware)

    # 注册路由
    from backend.routes.admin import router as admin_router
    from backend.routes.auth import router as auth_router
    from backend.routes.chat import router as chat_router
    from backend.routes.memory import router as memory_router
    from backend.routes.resume import router as resume_router
    from backend.routes.settings import router as settings_router
    app.include_router(admin_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(resume_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")

    # 前端由独立的 Next.js 服务提供（P2-3 起），生产环境通过 Nginx 反向代理
    # 不再挂载 StaticFiles

    return app


app = create_app()


def main() -> None:
    """CLI 入口：启动 uvicorn 服务器。"""
    import uvicorn

    host = os.environ.get("RESUME_AGENT_HOST", "0.0.0.0")
    port = int(os.environ.get("RESUME_AGENT_PORT", "8000"))
    uvicorn.run("backend.app:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
