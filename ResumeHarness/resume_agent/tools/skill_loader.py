"""技能加载工具，供 LLM 主动加载指定 Skill 的完整内容。"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from resume_agent.tools.base import BaseTool, ToolExecutionContext, ToolResult

log = logging.getLogger(__name__)


class SkillLoaderInput(BaseModel):
    """skill_loader 工具输入。"""

    skill_name: str = Field(
        default="resume-skill",
        description="要加载的技能名称",
    )


class SkillLoaderTool(BaseTool):
    """技能加载工具，供 LLM 主动加载指定 Skill 的完整内容。

    当需要重新获取简历优化知识时调用。
    """

    name = "skill_loader"
    description = (
        "加载指定技能文件的完整内容到当前上下文。"
        "当需要重新获取简历优化知识时调用。"
    )
    input_model = SkillLoaderInput

    async def execute(self, arguments: SkillLoaderInput, context: ToolExecutionContext) -> ToolResult:
        """执行技能加载。"""
        if arguments.skill_name != "resume-skill":
            return ToolResult(
                output=f"不支持的技能名称: {arguments.skill_name}，当前仅支持 'resume-skill'",
                is_error=True,
            )

        skill_path = Path(__file__).parent.parent / "skills" / "resume-skill.md"
        if not skill_path.exists():
            return ToolResult(
                output="简历优化技能文件 (resume-skill.md) 不存在",
                is_error=True,
            )

        try:
            content = skill_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            return ToolResult(output=f"读取技能文件失败: {exc}", is_error=True)

        return ToolResult(output=content)

    def is_read_only(self, arguments: SkillLoaderInput) -> bool:
        return True
