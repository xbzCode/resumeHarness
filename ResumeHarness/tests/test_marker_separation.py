# tests/test_marker_separation.py
import re

# 从 chat.py 复制核心常量和函数进行测试
_RESUME_MARKER_OPEN = "<!--RESUME-->"
_RESUME_MARKER_CLOSE = "<!--/RESUME-->"
_RESUME_MARKER_PATTERN = re.compile(r"<!--RESUME-->(.*?)<!--/RESUME-->", re.DOTALL)
_RESUME_SECTION_PATTERN = re.compile(
    r"^##\s+(?:个人简介|工作经历|教育背景|技能标签?|项目经历|Professional Summary|Work Experience|Education|Skills)",
    re.MULTILINE,
)
_RESUME_TITLE_PATTERN = re.compile(r"^#\s+[^#\n]+", re.MULTILINE)
_RESUME_VALID_SECTIONS = {
    "个人简介", "个人总结", "自我介绍", "简介", "总结",
    "工作经历", "工作经验", "职业经历",
    "教育背景", "教育经历", "学历",
    "专业技能", "技能", "核心技能", "技术栈", "技能标签",
    "项目经历", "项目经验", "核心项目",
    "profile", "summary", "about",
    "experience", "work experience", "employment",
    "education", "academic",
    "skills", "technical skills", "competencies",
    "projects", "project experience",
}

# 测试 _extract_resume_content 逻辑 + _StreamingMarkerFilter 逻辑
# ... （与之前 test_marker.py 相同）
