"""Skill 管理模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SKILLS_DIR = Path(__file__).parent

# 技能文件分类标签
_SKILL_CATEGORIES: dict[str, str] = {
    "resume-skill": "通用技能",
    "resume-tech": "行业技能-互联网/科技",
    "resume-finance": "行业技能-金融",
    "resume-jd": "JD 解析技能",
}


def list_skills() -> list[dict[str, Any]]:
    """列出可用的 Skill 文件。"""
    skills = []
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skill_info = get_skill_info(path.stem)
        # 附加分类标签
        if skill_info.get("found"):
            skill_info["category"] = _SKILL_CATEGORIES.get(path.stem, "其他")
        skills.append(skill_info)
    return skills


def get_skill_info(skill_name: str) -> dict[str, Any]:
    """获取指定 Skill 的信息。"""
    path = _SKILLS_DIR / f"{skill_name}.md"
    if not path.exists():
        return {"name": skill_name, "found": False}

    try:
        stat = path.stat()
        # 读取前 200 字符作为摘要
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        preview = content[:200] + "..." if len(content) > 200 else content
        return {
            "name": skill_name,
            "found": True,
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
            "preview": preview,
        }
    except OSError:
        return {"name": skill_name, "found": False}
