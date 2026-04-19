"""Skill 管理模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SKILLS_DIR = Path(__file__).parent


def list_skills() -> list[dict[str, Any]]:
    """列出可用的 Skill 文件。"""
    skills = []
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skills.append(get_skill_info(path.stem))
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
