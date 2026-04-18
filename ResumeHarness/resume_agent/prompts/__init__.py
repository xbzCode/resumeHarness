"""提示词组装模块。"""

from resume_agent.prompts.system_prompt import (
    RESUME_AGENT_SYSTEM_PROMPT,
    build_resume_system_prompt,
)

__all__ = [
    "RESUME_AGENT_SYSTEM_PROMPT",
    "build_resume_system_prompt",
]
