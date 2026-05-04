"""技能加载工具，供 LLM 主动加载指定 Skill 的完整内容。"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from resume_agent.skills.resume_skill import list_skills, load_skill_content
from resume_agent.tools.base import BaseTool, ToolExecutionContext, ToolResult

log = logging.getLogger(__name__)


class SkillLoaderInput(BaseModel):
    """skill_loader 工具输入。"""

    skill_name: str = Field(
        default="resume-skill",
        description="要加载的技能名称（如 resume-skill、resume-tech、resume-finance、resume-jd）",
    )


class SkillLoaderTool(BaseTool):
    """技能加载工具，供 LLM 主动加载指定 Skill 的完整内容。

    当需要获取特定领域知识时调用。支持所有已注册技能（含外部目录技能）。
    """

    name = "skill_loader"
    description = (
        "加载指定技能文件的完整内容到当前上下文。"
        "可用技能：resume-skill（通用简历优化）、resume-tech（互联网/科技行业）、"
        "resume-finance（金融行业）、resume-jd（JD 解析）。"
        "当需要获取特定领域的简历优化知识时调用。"
    )
    input_model = SkillLoaderInput
    category = "技能"
    is_read_only_default = True

    async def execute(self, arguments: SkillLoaderInput, context: ToolExecutionContext) -> ToolResult:
        """执行技能加载。"""
        skill_name = arguments.skill_name

        # 查找可用技能列表
        available = list_skills()
        available_names = [s["name"] for s in available if s.get("found")]

        if skill_name not in available_names:
            names_str = "、".join(available_names) if available_names else "无"
            return ToolResult(
                output=f"不支持的技能名称: {skill_name}。当前可用技能：{names_str}",
                is_error=True,
            )

        # 加载技能正文
        content = load_skill_content(skill_name)
        if content is None:
            return ToolResult(
                output=f"加载技能文件失败: {skill_name}",
                is_error=True,
            )

        return ToolResult(output=content)

    def is_read_only(self, arguments: SkillLoaderInput) -> bool:
        return True
