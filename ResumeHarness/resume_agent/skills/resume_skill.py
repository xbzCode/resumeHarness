"""Skill 管理模块。

支持 Markdown + YAML Front Matter 格式的技能文件。
- Front Matter 元数据用于分类、搜索、依赖管理和 Token 预算控制
- 行业→技能映射从 Front Matter 的 `industry` 字段自动构建
- 支持外部技能目录（extra_skill_dirs）
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SKILLS_DIR = Path(__file__).parent

# Front Matter 正则：---\n...\n---
_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# 技能名称格式校验
_SKILL_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# 文件大小上限 64KB
_MAX_SKILL_SIZE = 64 * 1024


# ---------------------------------------------------------------------------
# SkillMeta 数据模型
# ---------------------------------------------------------------------------


@dataclass
class SkillMeta:
    """技能元数据（从 YAML Front Matter 解析）。"""

    name: str
    version: str = "0.0.0"
    category: str = "其他"
    tags: list[str] = field(default_factory=list)
    industry: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    token_budget: int = 2000
    author: str = ""
    description: str = ""

    def validate(self) -> list[str]:
        """校验元数据，返回错误列表。"""
        errors: list[str] = []
        if not self.name:
            errors.append("name 为空")
        elif not _SKILL_NAME_RE.match(self.name):
            errors.append(f"name 格式无效: {self.name}（需匹配 ^[a-z][a-z0-9-]*$）")
        if not self.version:
            errors.append("version 为空")
        if not self.category:
            errors.append("category 为空")
        if not self.description:
            errors.append("description 为空")
        return errors


# ---------------------------------------------------------------------------
# Front Matter 解析
# ---------------------------------------------------------------------------


def _parse_yaml_front_matter(text: str) -> dict[str, Any]:
    """简易 YAML Front Matter 解析（不引入 pyyaml 依赖）。

    支持以下类型：
    - string: key: value
    - list: key: [a, b, c] 或 key:\n  - a\n  - b
    - int: key: 123
    """
    result: dict[str, Any] = {}
    lines = text.strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue

        # key: value
        colon_idx = line.find(":")
        if colon_idx < 0:
            i += 1
            continue

        key = line[:colon_idx].strip()
        value_part = line[colon_idx + 1:].strip()

        # 带引号的字符串
        if value_part.startswith('"') and value_part.endswith('"'):
            result[key] = value_part[1:-1]
            i += 1
            continue

        # 列表 [a, b, c]
        if value_part.startswith("[") and value_part.endswith("]"):
            items = [item.strip().strip('"').strip("'") for item in value_part[1:-1].split(",") if item.strip()]
            result[key] = items
            i += 1
            continue

        # 多行列表
        if not value_part:
            list_items: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- "):
                item = lines[j].strip()[2:].strip().strip('"').strip("'")
                if item:
                    list_items.append(item)
                j += 1
            if list_items:
                result[key] = list_items
                i = j
                continue

        # 整数
        try:
            result[key] = int(value_part)
            i += 1
            continue
        except ValueError:
            pass

        # 普通字符串
        result[key] = value_part
        i += 1

    return result


def parse_skill_front_matter(content: str) -> tuple[SkillMeta | None, str]:
    """解析技能文件内容，返回 (SkillMeta, 正文)。

    如果没有 Front Matter，返回 (None, 原文)。
    """
    match = _FM_PATTERN.match(content)
    if not match:
        return None, content

    fm_text = match.group(1)
    body = content[match.end():]

    raw = _parse_yaml_front_matter(fm_text)

    meta = SkillMeta(
        name=raw.get("name", ""),
        version=str(raw.get("version", "0.0.0")),
        category=raw.get("category", "其他"),
        tags=raw.get("tags", []) if isinstance(raw.get("tags"), list) else [],
        industry=raw.get("industry", []) if isinstance(raw.get("industry"), list) else [],
        depends=raw.get("depends", []) if isinstance(raw.get("depends"), list) else [],
        token_budget=int(raw.get("token_budget", 2000)) if raw.get("token_budget") else 2000,
        author=raw.get("author", ""),
        description=raw.get("description", ""),
    )

    return meta, body


# ---------------------------------------------------------------------------
# 技能目录扫描
# ---------------------------------------------------------------------------


def _scan_skill_dirs(extra_dirs: list[Path] | None = None) -> dict[str, Path]:
    """扫描所有技能目录，返回 {skill_name: file_path} 映射。

    外部目录的同名技能会覆盖内置技能。
    """
    skills: dict[str, Path] = {}

    # 1. 内置技能目录
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skills[path.stem] = path

    # 2. 外部技能目录（后加载的覆盖先加载的）
    if extra_dirs:
        for d in extra_dirs:
            d = Path(d)
            if d.is_dir():
                for path in sorted(d.glob("*.md")):
                    skills[path.stem] = path

    return skills


def _get_extra_skill_dirs() -> list[Path]:
    """从配置获取外部技能目录列表。"""
    try:
        settings = get_settings()
        dirs_str = getattr(settings, "extra_skill_dirs", "")
        if not dirs_str:
            return []
        if isinstance(dirs_str, str):
            return [Path(d.strip()) for d in dirs_str.split(",") if d.strip()]
        if isinstance(dirs_str, list):
            return [Path(d) for d in dirs_str if d]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def list_skills(extra_dirs: list[Path] | None = None) -> list[dict[str, Any]]:
    """列出可用的 Skill 文件。"""
    if extra_dirs is None:
        extra_dirs = _get_extra_skill_dirs()

    skill_map = _scan_skill_dirs(extra_dirs)
    result: list[dict[str, Any]] = []

    for skill_name, path in sorted(skill_map.items()):
        info = _load_skill_info(skill_name, path)
        result.append(info)

    return result


def get_skill_info(skill_name: str, extra_dirs: list[Path] | None = None) -> dict[str, Any]:
    """获取指定 Skill 的信息。"""
    if extra_dirs is None:
        extra_dirs = _get_extra_skill_dirs()

    skill_map = _scan_skill_dirs(extra_dirs)
    path = skill_map.get(skill_name)

    if path is None:
        return {"name": skill_name, "found": False}

    return _load_skill_info(skill_name, path)


def load_skill_content(skill_name: str, extra_dirs: list[Path] | None = None) -> str | None:
    """加载指定技能的正文内容（不含 Front Matter）。

    Returns:
        技能正文内容，文件不存在时返回 None
    """
    if extra_dirs is None:
        extra_dirs = _get_extra_skill_dirs()

    skill_map = _scan_skill_dirs(extra_dirs)
    path = skill_map.get(skill_name)

    if path is None:
        return None

    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None

    # 检查文件大小
    if len(content.encode("utf-8")) > _MAX_SKILL_SIZE:
        log.warning("技能文件过大，截断: %s (%d bytes)", skill_name, len(content.encode("utf-8")))
        content = content[:_MAX_SKILL_SIZE]

    # 去除 Front Matter，只返回正文
    _, body = parse_skill_front_matter(content)
    return body


def get_industry_skill_map(extra_dirs: list[Path] | None = None) -> dict[str, list[str]]:
    """构建 industry → [skill_name] 映射表。

    从所有技能的 Front Matter `industry` 字段自动构建。
    """
    if extra_dirs is None:
        extra_dirs = _get_extra_skill_dirs()

    skill_map = _scan_skill_dirs(extra_dirs)
    industry_map: dict[str, list[str]] = {}

    for skill_name, path in skill_map.items():
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue

        meta, _ = parse_skill_front_matter(content)
        if meta and meta.industry:
            for ind in meta.industry:
                industry_map.setdefault(ind, []).append(skill_name)

    return industry_map


def validate_skill_file(path: Path) -> list[str]:
    """校验技能文件格式，返回错误列表。

    校验规则：
    - Front Matter 必须存在且包含 name、version、category、description
    - name 必须与文件名 stem 一致
    - name 格式：^[a-z][a-z0-9-]*$
    - 文件大小不超过 64KB
    - 正文必须包含至少一个 ## 级标题
    """
    errors: list[str] = []

    # 文件大小
    try:
        size = path.stat().st_size
    except OSError as exc:
        return [f"无法读取文件: {exc}"]

    if size > _MAX_SKILL_SIZE:
        errors.append(f"文件过大: {size} bytes（上限 {_MAX_SKILL_SIZE} bytes）")

    # 读取内容
    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        return [f"读取文件失败: {exc}"]

    # 解析 Front Matter
    meta, body = parse_skill_front_matter(content)

    if meta is None:
        errors.append("缺少 YAML Front Matter（需以 --- 开头和结尾）")
        return errors

    # 校验元数据
    meta_errors = meta.validate()
    errors.extend(meta_errors)

    # name 与文件名一致
    if meta.name and meta.name != path.stem:
        errors.append(f"name({meta.name}) 与文件名({path.stem}) 不一致")

    # depends 中引用的技能必须存在（仅在全部技能目录中查找）
    if meta.depends:
        skill_map = _scan_skill_dirs()
        for dep in meta.depends:
            if dep not in skill_map:
                errors.append(f"依赖的技能不存在: {dep}")

    # 正文至少一个 ## 标题
    if not re.search(r"^## ", body, re.MULTILINE):
        errors.append("正文必须包含至少一个 ## 级标题")

    return errors


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _load_skill_info(skill_name: str, path: Path) -> dict[str, Any]:
    """从文件加载技能信息。"""
    try:
        stat = path.stat()
        content = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return {"name": skill_name, "found": False}

    meta, body = parse_skill_front_matter(content)

    # 预览：正文前 200 字符
    preview = body[:200] + "..." if len(body) > 200 else body

    info: dict[str, Any] = {
        "name": skill_name,
        "found": True,
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
        "preview": preview,
    }

    # 附加 Front Matter 元数据
    if meta:
        info.update({
            "version": meta.version,
            "category": meta.category,
            "tags": meta.tags,
            "industry": meta.industry,
            "depends": meta.depends,
            "token_budget": meta.token_budget,
            "author": meta.author,
            "description": meta.description,
        })

    return info


# 延迟导入避免循环依赖
def get_settings():
    """延迟导入 settings。"""
    from resume_agent.config.settings import get_settings as _get_settings
    return _get_settings()
