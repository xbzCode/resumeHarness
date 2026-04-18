"""Hook registry (simplified for P0).

从 OpenHarness 裁剪而来，P0 阶段仅保留空注册表。
"""

from __future__ import annotations

from typing import Any


class HookRegistry:
    """Store hooks grouped by event (P0: always empty)."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Any]] = {}

    def get(self, event: str) -> list[Any]:
        """Return hooks registered for an event."""
        return list(self._hooks.get(event, []))
