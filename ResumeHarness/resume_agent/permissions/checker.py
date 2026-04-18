"""Permission checking for tool execution.

从 OpenHarness 裁剪而来，精简为固定 FULL_AUTO 模式。
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass

from resume_agent.permissions.modes import PermissionMode

log = logging.getLogger(__name__)

SENSITIVE_PATH_PATTERNS: tuple[str, ...] = (
    "*/.ssh/*",
    "*/.aws/credentials",
    "*/.aws/config",
    "*/.config/gcloud/*",
    "*/.azure/*",
    "*/.gnupg/*",
    "*/.docker/config.json",
    "*/.kube/config",
    "*/.resume_agent/credentials.json",
)


@dataclass(frozen=True)
class PermissionDecision:
    """Result of checking whether a tool invocation may run."""

    allowed: bool
    requires_confirmation: bool = False
    reason: str = ""


class PermissionChecker:
    """Evaluate tool usage against the configured permission mode.

    ResumeHarness 默认 FULL_AUTO 模式，所有工具自动放行。
    """

    def __init__(self, mode: PermissionMode = PermissionMode.FULL_AUTO) -> None:
        self._mode = mode

    def evaluate(
        self,
        tool_name: str,
        *,
        is_read_only: bool,
        file_path: str | None = None,
        command: str | None = None,
    ) -> PermissionDecision:
        """Return whether the tool may run immediately."""
        if file_path:
            for candidate_path in _policy_match_paths(file_path):
                for pattern in SENSITIVE_PATH_PATTERNS:
                    if fnmatch.fnmatch(candidate_path, pattern):
                        return PermissionDecision(
                            allowed=False,
                            reason=(
                                f"Access denied: {file_path} is a sensitive credential path "
                                f"(matched built-in pattern '{pattern}')"
                            ),
                        )

        if self._mode == PermissionMode.FULL_AUTO:
            return PermissionDecision(allowed=True, reason="Auto mode allows all tools")

        if is_read_only:
            return PermissionDecision(allowed=True, reason="read-only tools are allowed")

        return PermissionDecision(
            allowed=False,
            requires_confirmation=True,
            reason="Mutating tools require user confirmation in default mode",
        )


def _policy_match_paths(file_path: str) -> tuple[str, ...]:
    """Return path forms that should participate in policy matching."""
    normalized = file_path.rstrip("/")
    if not normalized:
        return (file_path,)
    return (normalized, normalized + "/")
