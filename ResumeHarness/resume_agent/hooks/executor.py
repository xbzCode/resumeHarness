"""Hook execution engine (simplified for P0).

从 OpenHarness 裁剪而来，P0 阶段为空实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resume_agent.hooks.loader import HookRegistry


@dataclass
class AggregatedHookResult:
    """Result of executing hooks for an event."""

    blocked: bool = False
    reason: str = ""


class HookExecutor:
    """Execute hooks for lifecycle events (P0: no-op)."""

    def __init__(self, registry: HookRegistry | None = None, context: Any = None) -> None:
        self._registry = registry or HookRegistry()
        self._context = context

    async def execute(self, event: str, payload: dict[str, Any]) -> AggregatedHookResult:
        """Execute all matching hooks for an event (P0: always returns not blocked)."""
        return AggregatedHookResult()
