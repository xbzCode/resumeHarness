"""简历结构化数据模型。

将 LLM 输出的 Markdown 简历解析为结构化的 Pydantic 模型，
实现数据与展示分离，前端组件渲染和 PDF 渲染共用同一份数据。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """联系方式"""

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    website: str | None = None
    linkedin: str | None = None
    wechat: str | None = None
    raw_text: str | None = Field(
        default=None,
        description="原始联系方式文本，当无法结构化解析时作为兜底",
    )


class WorkExperience(BaseModel):
    """工作经历"""

    title: str = Field(description="职位名称")
    company: str = Field(description="公司/组织名称")
    period: str = Field(description="时间段，格式 YYYY.MM - YYYY.MM 或 YYYY.MM - 至今")
    highlights: list[str] = Field(default_factory=list, description="核心成果列表")


class Education(BaseModel):
    """教育背景"""

    degree: str = Field(description="学位，如 本科/硕士/博士")
    major: str = Field(description="专业")
    school: str = Field(description="学校名称")
    period: str = Field(description="时间段")
    achievements: list[str] = Field(default_factory=list, description="关键成就或 GPA")


class SkillCategory(BaseModel):
    """技能分类"""

    category: str = Field(description="技能类别名称，如 编程语言/框架/工具/软技能")
    skills: list[str] = Field(default_factory=list, description="技能列表")


class ProjectExperience(BaseModel):
    """项目经历"""

    name: str = Field(description="项目名称")
    role: str | None = Field(default=None, description="角色")
    period: str | None = Field(default=None, description="时间段")
    description: str | None = Field(default=None, description="项目描述")
    contributions: list[str] = Field(default_factory=list, description="核心贡献")


class ResumeData(BaseModel):
    """简历结构化数据模型。

    所有简历内容解析后的统一数据结构，前端组件渲染和 PDF 渲染共用。
    """

    name: str = Field(description="姓名")
    contact: ContactInfo = Field(default_factory=ContactInfo, description="联系方式")
    summary: str | None = Field(default=None, description="个人简介")
    experience: list[WorkExperience] = Field(
        default_factory=list, description="工作经历（按时间倒序）"
    )
    education: list[Education] = Field(
        default_factory=list, description="教育背景（按时间倒序）"
    )
    skills: list[SkillCategory] = Field(
        default_factory=list, description="专业技能（按分类）"
    )
    projects: list[ProjectExperience] = Field(
        default_factory=list, description="项目经历（按时间倒序）"
    )
    section_order: list[str] | None = Field(
        default=None,
        description="章节显示顺序，如 ['summary', 'experience', 'education', 'skills', 'projects']",
    )

    def has_content(self) -> bool:
        """检查简历是否有实质内容（至少有姓名和一个章节）。"""
        if not self.name:
            return False
        return bool(
            self.summary
            or self.experience
            or self.education
            or self.skills
            or self.projects
        )

    def to_template_context(self) -> dict:
        """转换为 Jinja2 模板上下文字典。

        提供模板中常用的辅助属性，如联系方式格式化文本等。
        """
        contact_parts: list[str] = []
        if self.contact.email:
            contact_parts.append(self.contact.email)
        if self.contact.phone:
            contact_parts.append(self.contact.phone)
        if self.contact.location:
            contact_parts.append(self.contact.location)
        if self.contact.website:
            contact_parts.append(self.contact.website)
        if self.contact.linkedin:
            contact_parts.append(self.contact.linkedin)
        if self.contact.wechat:
            contact_parts.append(f"微信: {self.contact.wechat}")
        if not contact_parts and self.contact.raw_text:
            contact_parts.append(self.contact.raw_text)

        # 计算有内容的章节，并按 section_order 排序
        default_order = ["summary", "experience", "education", "skills", "projects"]
        order = self.section_order or default_order
        has_content_map = {
            "summary": bool(self.summary),
            "experience": bool(self.experience),
            "education": bool(self.education),
            "skills": bool(self.skills),
            "projects": bool(self.projects),
        }
        # 按 section_order 排序，只包含有内容的章节
        sections: list[str] = []
        for key in order:
            if key in has_content_map and has_content_map[key] and key not in sections:
                sections.append(key)
        # 补充 section_order 中未包含但有内容的章节
        for key in default_order:
            if has_content_map[key] and key not in sections:
                sections.append(key)

        return {
            "resume": self,
            "contact_text": " | ".join(contact_parts),
            "has_experience": bool(self.experience),
            "has_education": bool(self.education),
            "has_skills": bool(self.skills),
            "has_projects": bool(self.projects),
            "has_summary": bool(self.summary),
            "sections": sections,
        }
