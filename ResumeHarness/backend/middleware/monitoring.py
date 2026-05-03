"""基础监控中间件。

记录请求量、延迟、错误率，定期汇总输出日志。
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("resume_agent.monitor")


@dataclass
class _RequestMetrics:
    """请求指标收集器。"""

    total_requests: int = 0
    error_requests: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    # 按路径统计
    path_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    path_errors: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    path_latencies: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    # 按状态码统计
    status_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))


class MonitoringMiddleware(BaseHTTPMiddleware):
    """基础监控中间件。

    收集请求量、延迟、错误率指标，定期输出汇总日志。
    """

    def __init__(self, app, log_interval: int = 60) -> None:
        super().__init__(app)
        self._metrics = _RequestMetrics()
        self._log_interval = log_interval
        self._lock = asyncio.Lock()
        self._log_task: asyncio.Task | None = None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # 非 API 路径不监控
        if not path.startswith("/api/"):
            return await call_next(request)

        start_time = time.monotonic()
        response: Response | None = None
        error_occurred = False

        try:
            response = await call_next(request)
            return response
        except Exception:
            error_occurred = True
            raise
        finally:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            status_code = response.status_code if response else 500

            async with self._lock:
                m = self._metrics
                m.total_requests += 1
                m.total_latency_ms += elapsed_ms
                m.max_latency_ms = max(m.max_latency_ms, elapsed_ms)
                m.path_counts[path] += 1
                m.path_latencies[path] += elapsed_ms
                m.status_counts[status_code] += 1

                if error_occurred or status_code >= 400:
                    m.error_requests += 1
                    m.path_errors[path] += 1

    def get_metrics(self) -> dict[str, Any]:
        """获取当前监控指标。"""
        m = self._metrics
        avg_latency = m.total_latency_ms / m.total_requests if m.total_requests > 0 else 0
        error_rate = m.error_requests / m.total_requests if m.total_requests > 0 else 0

        # 按路径汇总
        paths: dict[str, Any] = {}
        for path, count in m.path_counts.items():
            paths[path] = {
                "count": count,
                "errors": m.path_errors.get(path, 0),
                "avg_latency_ms": round(m.path_latencies.get(path, 0) / count, 1),
            }

        return {
            "total_requests": m.total_requests,
            "error_requests": m.error_requests,
            "error_rate": round(error_rate, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "max_latency_ms": round(m.max_latency_ms, 1),
            "status_codes": dict(m.status_counts),
            "paths": paths,
        }

    def start_periodic_log(self) -> None:
        """启动定期日志输出。"""
        if self._log_task is not None:
            return

        async def _periodic_log() -> None:
            while True:
                await asyncio.sleep(self._log_interval)
                metrics = self.get_metrics()
                if metrics["total_requests"] == 0:
                    continue

                logger.info(
                    "📊 监控汇总: 请求=%d 错误=%d(%.1f%%) "
                    "平均延迟=%.0fms 最大延迟=%.0fms",
                    metrics["total_requests"],
                    metrics["error_requests"],
                    metrics["error_rate"] * 100,
                    metrics["avg_latency_ms"],
                    metrics["max_latency_ms"],
                )

                # 输出热点路径
                top_paths = sorted(
                    metrics["paths"].items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )[:5]
                for path, info in top_paths:
                    logger.info(
                        "  %s: %d次, 错误%d次, 平均%.0fms",
                        path, info["count"], info["errors"], info["avg_latency_ms"],
                    )

        self._log_task = asyncio.create_task(_periodic_log())

    def stop_periodic_log(self) -> None:
        """停止定期日志输出。"""
        if self._log_task is not None:
            self._log_task.cancel()
            self._log_task = None
