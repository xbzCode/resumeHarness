"""简历模板注册表与元数据管理。

支持两种模板目录结构：
1. 扁平结构（向后兼容）：templates/professional.html + templates/professional.css
2. 子目录结构（规范推荐）：templates/professional/template.json + template.html + preview.png

template.json 元数据规范参考 docs/后续优化.md 2.3 节。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent

# 模板名称格式校验
_TEMPLATE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

# HTML 模板最大文件大小 256KB
_MAX_TEMPLATE_SIZE = 256 * 1024


@dataclass
class TemplateMeta:
    """模板元数据（从 template.json 解析）。"""

    name: str = ""
    version: str = "1.0.0"
    display_name: str = ""
    description: str = ""
    author: str = ""
    layout: str = ""
    color_scheme: dict[str, str] = field(default_factory=dict)
    recommended_industries: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    supports_dark_mode: bool = False
    page_size: str = "A4"
    preview: str = ""

    def validate(self) -> list[str]:
        """校验元数据，返回错误列表。"""
        errors: list[str] = []
        if not self.name:
            errors.append("name 为空")
        elif not _TEMPLATE_NAME_RE.match(self.name):
            errors.append(f"name 格式无效: {self.name}")
        if not self.display_name:
            errors.append("display_name 为空")
        if not self.description:
            errors.append("description 为空")
        return errors


# ---------------------------------------------------------------------------
# 模板发现与注册
# ---------------------------------------------------------------------------


def _discover_templates() -> dict[str, Path]:
    """发现所有模板，返回 {template_name: template_dir} 映射。

    同时支持子目录结构和扁平结构：
    - 子目录：templates/{name}/template.json
    - 扁平：templates/{name}.html + templates/{name}.json（可选）
    """
    templates: dict[str, Path] = {}

    # 1. 子目录结构：templates/{name}/template.json
    for subdir in sorted(TEMPLATES_DIR.iterdir()):
        if subdir.is_dir() and (subdir / "template.json").exists():
            templates[subdir.name] = subdir

    # 2. 扁平结构：templates/{name}.html（向后兼容，子目录优先）
    for html_file in sorted(TEMPLATES_DIR.glob("*.html")):
        name = html_file.stem
        if name not in templates:
            templates[name] = TEMPLATES_DIR

    return templates


def list_templates() -> list[dict[str, Any]]:
    """列出所有可用模板。"""
    template_map = _discover_templates()
    result: list[dict[str, Any]] = []

    for name, template_dir in sorted(template_map.items()):
        info = _load_template_info(name, template_dir)
        result.append(info)

    return result


def get_template_info(template_name: str) -> dict[str, Any] | None:
    """获取指定模板的详细信息。"""
    template_map = _discover_templates()
    template_dir = template_map.get(template_name)
    if template_dir is None:
        return None
    return _load_template_info(template_name, template_dir)


def get_template_html_path(template_name: str) -> Path | None:
    """获取模板 HTML 文件路径。"""
    template_map = _discover_templates()
    template_dir = template_map.get(template_name)
    if template_dir is None:
        return None

    # 子目录结构
    subdir_html = template_dir / f"{template_name}.html"
    if subdir_html.exists():
        return subdir_html

    # 子目录结构（template.html）
    generic_html = template_dir / "template.html"
    if generic_html.exists():
        return generic_html

    # 扁平结构
    flat_html = TEMPLATES_DIR / f"{template_name}.html"
    if flat_html.exists():
        return flat_html

    return None


def validate_template(template_name: str) -> list[str]:
    """校验模板格式，返回错误列表。"""
    template_map = _discover_templates()
    template_dir = template_map.get(template_name)
    if template_dir is None:
        return [f"模板不存在: {template_name}"]

    errors: list[str] = []

    # 检查 HTML 文件
    html_path = get_template_html_path(template_name)
    if html_path is None:
        errors.append("缺少 HTML 模板文件")
    else:
        # HTML 文件大小
        try:
            html_size = html_path.stat().st_size
            if html_size > _MAX_TEMPLATE_SIZE:
                errors.append(f"HTML 文件过大: {html_size} bytes")
        except OSError:
            errors.append("无法读取 HTML 文件")

        # HTML 内容检查
        try:
            html_content = html_path.read_text(encoding="utf-8", errors="replace")
            if "{{ resume.name }}" not in html_content and "{{resume.name}}" not in html_content:
                errors.append("HTML 模板必须包含 {{ resume.name }} 变量引用")
            if "@page" not in html_content:
                errors.append("HTML 模板必须包含 @page CSS 规则")
        except OSError:
            errors.append("读取 HTML 文件失败")

    # 检查 template.json
    meta_path = template_dir / "template.json"
    if not meta_path.exists() and template_dir == TEMPLATES_DIR:
        meta_path = TEMPLATES_DIR / f"{template_name}.json"
    if meta_path.exists():
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
            meta = TemplateMeta(
                name=raw.get("name", ""),
                version=raw.get("version", "1.0.0"),
                display_name=raw.get("display_name", ""),
                description=raw.get("description", ""),
                author=raw.get("author", ""),
                layout=raw.get("layout", ""),
                color_scheme=raw.get("color_scheme", {}),
                recommended_industries=raw.get("recommended_industries", []),
                required_fields=raw.get("required_fields", []),
                optional_fields=raw.get("optional_fields", []),
                supports_dark_mode=raw.get("supports_dark_mode", False),
                page_size=raw.get("page_size", "A4"),
                preview=raw.get("preview", ""),
            )
            meta_errors = meta.validate()
            errors.extend(meta_errors)

            # name 与目录名一致
            if meta.name and meta.name != template_name:
                errors.append(f"name({meta.name}) 与目录名({template_name}) 不一致")

        except json.JSONDecodeError as exc:
            errors.append(f"template.json 解析失败: {exc}")
    else:
        # 扁平结构没有 template.json，给出提示
        if template_dir == TEMPLATES_DIR:
            pass  # 扁平结构正常，不报错

    return errors


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _load_template_info(name: str, template_dir: Path) -> dict[str, Any]:
    """从目录加载模板信息。"""
    info: dict[str, Any] = {
        "name": name,
        "found": True,
    }

    # 尝试读取 template.json
    # 子目录结构：template_dir/template.json
    # 扁平结构：TEMPLATES_DIR/{name}.json
    meta_path = template_dir / "template.json"
    if not meta_path.exists() and template_dir == TEMPLATES_DIR:
        meta_path = TEMPLATES_DIR / f"{name}.json"

    if meta_path.exists():
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
            info.update({
                "version": raw.get("version", "1.0.0"),
                "display_name": raw.get("display_name", name),
                "description": raw.get("description", ""),
                "author": raw.get("author", ""),
                "layout": raw.get("layout", ""),
                "color_scheme": raw.get("color_scheme", {}),
                "recommended_industries": raw.get("recommended_industries", []),
                "required_fields": raw.get("required_fields", []),
                "optional_fields": raw.get("optional_fields", []),
                "supports_dark_mode": raw.get("supports_dark_mode", False),
                "page_size": raw.get("page_size", "A4"),
                "preview": raw.get("preview", ""),
            })
        except (json.JSONDecodeError, OSError):
            info["display_name"] = name
            info["description"] = ""
    else:
        # 扁平结构的默认值
        display_names = {
            "professional": "简洁商务",
            "academic": "学术风",
            "creative": "创意排版",
        }
        descriptions = {
            "professional": "双栏侧边栏布局，适用于互联网/科技行业",
            "academic": "传统单栏居中布局，教育背景优先",
            "creative": "卡片式布局，渐变色块，适用于设计/市场",
        }
        info["display_name"] = display_names.get(name, name)
        info["description"] = descriptions.get(name, "")
        info["version"] = "1.0.0"

    # 检查 HTML 文件
    html_path = get_template_html_path(name)
    info["has_html"] = html_path is not None

    # 检查预览图
    preview_name = info.get("preview", "preview.png")
    preview_path = template_dir / preview_name if template_dir.is_dir() else None
    if preview_path and preview_path.exists():
        info["has_preview"] = True
    else:
        info["has_preview"] = False

    return info
