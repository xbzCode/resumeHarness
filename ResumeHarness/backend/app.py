"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.auth import AuthMiddleware
from backend.middleware.monitoring import MonitoringMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from resume_agent.config.settings import get_settings, validate_api_config
from resume_agent.db import close_db, get_db
from resume_agent.session_pool import ResumeSessionPool

logger = logging.getLogger(__name__)

# 全局会话池
session_pool: ResumeSessionPool | None = None

# 全局中间件引用（供状态查询 API 使用）
_rate_limit_middleware: RateLimitMiddleware | None = None
_monitoring_middleware: MonitoringMiddleware | None = None


def get_rate_limit_middleware() -> RateLimitMiddleware | None:
    """获取速率限制中间件实例。"""
    return _rate_limit_middleware


def get_monitoring_middleware() -> MonitoringMiddleware | None:
    """获取监控中间件实例。"""
    return _monitoring_middleware


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
    db = await get_db()
    logger.info("数据库已初始化")

    # 初始化 MCP 工具
    try:
        from resume_agent.runtime import init_mcp_tools, shutdown_mcp
        mcp_count = await init_mcp_tools()
        logger.info("MCP 工具初始化完成，注册 %d 个工具", mcp_count)
    except Exception as exc:
        logger.warning("MCP 工具初始化失败（不影响主服务）: %s", exc)

    # 启动会话池
    settings = get_settings()
    session_pool = ResumeSessionPool(
        max_sessions=settings.max_sessions,
        idle_timeout=settings.idle_timeout,
    )
    await session_pool.start()
    logger.info("会话池已启动 (max=%d, idle_timeout=%ds)", settings.max_sessions, settings.idle_timeout)

    # 启动监控定期日志
    if _monitoring_middleware is not None and settings.monitor_enabled:
        _monitoring_middleware.start_periodic_log()
        logger.info("监控定期日志已启动 (间隔=%ds)", settings.monitor_log_interval)

    yield

    # 停止监控定期日志
    if _monitoring_middleware is not None:
        _monitoring_middleware.stop_periodic_log()
        logger.info("监控定期日志已停止")

    # 关闭 MCP 连接
    try:
        from resume_agent.runtime import shutdown_mcp
        await shutdown_mcp()
    except Exception as exc:
        logger.warning("MCP 关闭异常: %s", exc)

    # 关闭共享 API 客户端连接池
    try:
        from resume_agent.runtime import close_shared_api_client
        await close_shared_api_client()
    except Exception as exc:
        logger.warning("API 客户端关闭异常: %s", exc)

    # 关闭会话池
    if session_pool is not None:
        await session_pool.stop()
        logger.info("会话池已关闭")

    # 关闭数据库
    await close_db()
    logger.info("数据库已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    global _rate_limit_middleware, _monitoring_middleware

    settings = get_settings()

    app = FastAPI(
        title="Resume Agent",
        description="简历智能体 Web API",
        version="0.2.0",
        lifespan=lifespan,
    )

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

    # -----------------------------------------------------------------------
    # 中间件栈（从内到外：CORS → Auth → RateLimit → Monitoring）
    # 使用纯 ASGI 中间件替代 BaseHTTPMiddleware，避免 body 消费导致的挂起问题
    # 注意：app.add_middleware 添加顺序是"后添加的先执行"，所以最外层的先 add
    # -----------------------------------------------------------------------

    # 监控中间件（最外层，记录所有请求）
    if settings.monitor_enabled:
        app.add_middleware(MonitoringMiddleware, log_interval=settings.monitor_log_interval)
        _monitoring_middleware = _find_middleware(app, MonitoringMiddleware)
        logger.info("监控中间件已启用 (interval=%ds)", settings.monitor_log_interval)

    # 速率限制中间件（在认证之后，可读取 user_id）
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware, rpm=settings.rate_limit_rpm, max_wait=settings.rate_limit_max_wait)
        _rate_limit_middleware = _find_middleware(app, RateLimitMiddleware)
        logger.info("速率限制中间件已启用 (rpm=%d)", settings.rate_limit_rpm)

    # JWT 认证中间件（在 CORS 之后，CORS preflight 不受影响）
    app.add_middleware(AuthMiddleware)

    # CORS — 使用可配置的白名单
    cors_origins = settings.cors_allowed_origins
    if not cors_origins:
        cors_origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 前端由独立的 Next.js 服务提供（P2-3 起），生产环境通过 Nginx 反向代理
    # 不再挂载 StaticFiles

    return app


def _find_middleware(app: FastAPI, cls: type) -> Any:
    """从 FastAPI 中间件栈中查找指定类型的中间件实例。"""
    # 遍历 Starlette 内部中间件链
    layer = getattr(app, "middleware_stack", None) or getattr(app, "_middleware_stack", None)
    while layer is not None:
        if isinstance(layer, cls):
            return layer
        # 纯 ASGI 中间件包装在 MiddlewareWrapper 中，其 .app 属性指向下一层
        layer = getattr(layer, "app", None)
    return None


app = create_app()


def main() -> None:
    """CLI 入口：启动 uvicorn 服务器。"""
    import uvicorn

    host = os.environ.get("RESUME_AGENT_HOST", "0.0.0.0")
    port = int(os.environ.get("RESUME_AGENT_PORT", "8000"))
    uvicorn.run("backend.app:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
