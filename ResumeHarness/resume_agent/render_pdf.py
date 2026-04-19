"""Markdown → PDF 渲染，使用 fpdf2（中文支持好，无需系统依赖）。"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

from resume_agent.exceptions import ResumeRenderError

log = logging.getLogger(__name__)

# Windows 系统字体目录
_FONTS_DIR = Path("C:/Windows/Fonts")

# 中文字体候选
_FONT_CANDIDATES = [
    ("SimHei", "simhei.ttf"),   # 黑体
    ("SimFang", "simfang.ttf"),  # 仿宋
    ("SimKai", "simkai.ttf"),   # 楷体
]


def _find_chinese_font() -> tuple[str, Path]:
    """查找可用的中文 TTF 字体，返回 (注册名, 路径)。"""
    for name, filename in _FONT_CANDIDATES:
        path = _FONTS_DIR / filename
        if path.exists():
            return name, path
    # 项目内置字体回退
    local_path = Path(__file__).parent / "templates" / "fonts" / "simhei.ttf"
    if local_path.exists():
        return "SimHei", local_path
    raise ResumeRenderError("未找到可用的中文字体，无法生成 PDF")


def _register_font(pdf, font_name: str, font_path: Path) -> None:
    """注册字体到 fpdf2。"""
    pdf.add_font(font_name, "", str(font_path))
    # fpdf2 的 add_font 会自动检测 bold/italic 变体
    # 如果没有 bold 变体，用 regular 替代
    bold_path = font_path.parent / font_path.name.replace(".ttf", "bd.ttf")
    if not bold_path.exists():
        # 黑体自身就是粗体，直接复用
        pdf.add_font(font_name, "B", str(font_path))
    else:
        pdf.add_font(font_name, "B", str(bold_path))


def render_markdown_to_pdf(markdown_content: str, template: str = "professional") -> bytes:
    """将 Markdown 渲染为 PDF 字节。

    Args:
        markdown_content: Markdown 格式的简历内容
        template: CSS 模板名称（用于选择配色）

    Returns:
        PDF 字节数据
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise ResumeRenderError(
            "fpdf2 未安装，无法渲染 PDF。请运行: pip install fpdf2"
        )

    font_name, font_path = _find_chinese_font()

    # 模板配色
    colors = _get_template_colors(template)

    # 解析 Markdown 为结构化块
    blocks = _parse_markdown_blocks(markdown_content)

    # 创建 PDF
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=20, top=20, right=20)
    _register_font(pdf, font_name, font_path)

    pdf.add_page()

    for block_type, content, level in blocks:
        if block_type == "h":
            _render_heading(pdf, content, level, font_name, colors)
        elif block_type == "li":
            _render_list_item(pdf, content, font_name, colors, level)
        elif block_type == "p":
            _render_paragraph(pdf, content, font_name, colors)
        elif block_type == "hr":
            _render_hr(pdf, colors)
        elif block_type == "blank":
            pdf.ln(2)

    return pdf.output()


def _get_template_colors(template: str) -> dict[str, tuple[int, int, int]]:
    """获取模板配色方案。"""
    if template == "academic":
        return {
            "h1": (0x1a, 0x1a, 0x2e),
            "h2": (0x2c, 0x3e, 0x50),
            "h3": (0x34, 0x49, 0x5e),
            "text": (0x33, 0x33, 0x33),
            "accent": (0x8e, 0x44, 0xad),
            "line": (0xbd, 0xc3, 0xc7),
        }
    elif template == "creative":
        return {
            "h1": (0x2c, 0x3e, 0x50),
            "h2": (0xe7, 0x4c, 0x3c),
            "h3": (0x34, 0x49, 0x5e),
            "text": (0x33, 0x33, 0x33),
            "accent": (0xe7, 0x4c, 0x3c),
            "line": (0xe7, 0x4c, 0x3c),
        }
    else:  # professional
        return {
            "h1": (0x2c, 0x3e, 0x50),
            "h2": (0x2c, 0x3e, 0x50),
            "h3": (0x34, 0x49, 0x5e),
            "text": (0x33, 0x33, 0x33),
            "accent": (0x34, 0x98, 0xdb),
            "line": (0xbd, 0xc3, 0xc7),
        }


def _parse_markdown_blocks(md: str) -> list[tuple[str, str, int]]:
    """解析 Markdown 为结构化块列表。

    Returns:
        [(block_type, content, level), ...]
        block_type: "h" | "li" | "p" | "hr" | "blank"
        level: heading level (1-6) or list indent level
    """
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            blocks.append(("blank", "", 0))
            i += 1
            continue

        # 水平线
        if re.match(r"^[-*_]{3,}\s*$", line.strip()):
            blocks.append(("hr", "", 0))
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            content = _strip_inline_md(m.group(2))
            blocks.append(("h", content, level))
            i += 1
            continue

        # 无序列表
        m = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
        if m:
            indent = len(m.group(1)) // 2
            content = _strip_inline_md(m.group(2))
            blocks.append(("li", content, indent))
            i += 1
            continue

        # 有序列表
        m = re.match(r"^(\s*)\d+\.\s+(.+)$", line)
        if m:
            indent = len(m.group(1)) // 2
            content = _strip_inline_md(m.group(2))
            blocks.append(("li", content, indent))
            i += 1
            continue

        # 普通段落（合并连续行）
        para_lines = [line]
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            if not next_line.strip():
                break
            if re.match(r"^(#{1,6}\s|[-*+]\s|\d+\.\s|[-*_]{3,}\s*$)", next_line):
                break
            para_lines.append(next_line)
            i += 1
        content = _strip_inline_md(" ".join(l.strip() for l in para_lines))
        blocks.append(("p", content, 0))
        i += 1

    return blocks


def _strip_inline_md(text: str) -> str:
    """去除行内 Markdown 格式（粗体、斜体、链接等），保留纯文本。"""
    # 去除 emoji（SimHei 不支持）
    text = re.sub(r"[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]", "", text)
    # 去除常用特殊符号
    text = text.replace("✅", "[v]").replace("📌", "").replace("•", "-")
    # 粗体+斜体
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    # 粗体
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # 斜体
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # 链接 [text](url)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # 行内代码
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _render_heading(
    pdf, content: str, level: int,
    font_name: str, colors: dict
) -> None:
    """渲染标题。"""
    if level == 1:
        pdf.set_font(font_name, "B", 18)
        pdf.set_text_color(*colors["h1"])
        pdf.cell(0, 12, content, new_x="LMARGIN", new_y="NEXT")
        # 下划线
        pdf.set_draw_color(*colors["accent"])
        pdf.set_line_width(0.8)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)
    elif level == 2:
        pdf.ln(3)
        pdf.set_font(font_name, "B", 14)
        pdf.set_text_color(*colors["h2"])
        pdf.cell(0, 10, content, new_x="LMARGIN", new_y="NEXT")
        # 下划线
        pdf.set_draw_color(*colors["line"])
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(3)
    elif level == 3:
        pdf.ln(2)
        pdf.set_font(font_name, "B", 12)
        pdf.set_text_color(*colors["h3"])
        pdf.cell(0, 8, content, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    else:
        pdf.set_font(font_name, "B", 11)
        pdf.set_text_color(*colors["h3"])
        pdf.cell(0, 7, content, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


def _render_paragraph(
    pdf, content: str,
    font_name: str, colors: dict
) -> None:
    """渲染段落。"""
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(*colors["text"])
    pdf.multi_cell(0, 6, content)
    pdf.ln(1)


def _render_list_item(
    pdf, content: str,
    font_name: str, colors: dict,
    indent: int = 0
) -> None:
    """渲染列表项。"""
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(*colors["text"])

    left = pdf.l_margin + indent * 8
    bullet = "- " if indent == 0 else "  - "
    pdf.set_x(left)
    # 先输出 bullet，再输出内容
    bullet_width = pdf.get_string_width(bullet)
    pdf.cell(bullet_width, 6, bullet)

    # 多行内容
    content_width = pdf.w - pdf.r_margin - left - bullet_width
    pdf.multi_cell(content_width, 6, content)
    pdf.ln(0.5)


def _render_hr(pdf, colors: dict) -> None:
    """渲染水平线。"""
    pdf.ln(2)
    pdf.set_draw_color(*colors["line"])
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
