"""简历 PDF 渲染引擎。

支持两种渲染路径：
1. 结构化渲染（主路径）：ResumeData + Jinja2 HTML 模板 → weasyprint/xhtml2pdf → PDF
2. Markdown 渲染（降级路径）：Markdown → HTML + CSS → weasyprint/xhtml2pdf/fpdf2 → PDF

渲染优先级：weasyprint → xhtml2pdf → fpdf2（逐级降级）

weasyprint: CSS 支持最完整，排版质量最高，需 GTK 运行时（Linux 原生支持，Windows 需额外安装）
xhtml2pdf: 纯 Python，CSS 2.1 子集，无系统依赖，跨平台（需手动注册中文字体）
fpdf2: 直接 Markdown→PDF，不支持 HTML+CSS，作为最后降级
"""

from __future__ import annotations

import io
import logging
import platform
from pathlib import Path
from typing import Any

from resume_agent.exceptions import ResumeRenderError

log = logging.getLogger(__name__)

# 渲染后端检测（惰性检测，只在首次使用时执行）
_backend_cache: str | None = None

# 中文字体是否已注册到 reportlab/xhtml2pdf
_font_registered: bool = False


def detect_pdf_backend() -> str:
    """检测可用的 PDF 渲染后端，返回 'weasyprint' | 'xhtml2pdf' | 'fpdf2'。"""
    global _backend_cache
    if _backend_cache is not None:
        return _backend_cache

    # 1. 尝试 weasyprint
    try:
        from weasyprint import HTML  # noqa: F401

        _backend_cache = "weasyprint"
        log.info("PDF 渲染后端: weasyprint（高质量）")
        return _backend_cache
    except Exception as exc:
        log.debug("weasyprint 不可用: %s", exc)

    # 2. 尝试 xhtml2pdf
    try:
        from xhtml2pdf import pisa  # noqa: F401

        _backend_cache = "xhtml2pdf"
        log.info("PDF 渲染后端: xhtml2pdf（中等质量）")
        return _backend_cache
    except Exception as exc:
        log.debug("xhtml2pdf 不可用: %s", exc)

    # 3. 降级到 fpdf2
    try:
        from fpdf import FPDF  # noqa: F401

        _backend_cache = "fpdf2"
        log.info("PDF 渲染后端: fpdf2（基础质量）")
        return _backend_cache
    except Exception:
        raise ResumeRenderError(
            "无可用的 PDF 渲染后端。请安装 weasyprint、xhtml2pdf 或 fpdf2 中的至少一个。"
        )


# ---------------------------------------------------------------------------
# 结构化渲染：ResumeData + Jinja2 HTML 模板
# ---------------------------------------------------------------------------

def render_resume_data_to_html(
    resume_data: Any,  # ResumeData，用 Any 避免循环导入
    template: str = "professional",
) -> str:
    """使用 Jinja2 模板引擎将 ResumeData 渲染为完整 HTML。

    Args:
        resume_data: 简历结构化数据（ResumeData 实例）
        template: 模板名称

    Returns:
        完整 HTML 字符串
    """
    from jinja2 import Environment, FileSystemLoader

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    tmpl = env.get_template(f"{template}.html")

    context = resume_data.to_template_context()
    return tmpl.render(**context)


def render_resume_data_to_pdf(
    resume_data: Any,
    template: str = "professional",
) -> bytes:
    """将 ResumeData 通过 Jinja2 模板渲染为 PDF。

    渲染路径：ResumeData → Jinja2 HTML 模板 → 完整 HTML → weasyprint/xhtml2pdf → PDF

    Args:
        resume_data: 简历结构化数据（ResumeData 实例）
        template: 模板名称

    Returns:
        PDF 字节数据
    """
    html = render_resume_data_to_html(resume_data, template)
    return _html_to_pdf(html, template)


# ---------------------------------------------------------------------------
# HTML → PDF 渲染（统一入口）
# ---------------------------------------------------------------------------

def _html_to_pdf(html: str, template: str = "professional") -> bytes:
    """将完整 HTML 文档渲染为 PDF，自动选择最佳后端。"""
    backend = detect_pdf_backend()

    if backend == "weasyprint":
        try:
            return _html_to_pdf_weasyprint(html)
        except Exception as exc:
            log.warning("weasyprint 渲染失败，降级到 xhtml2pdf: %s", exc)
            try:
                return _html_to_pdf_xhtml2pdf(html)
            except Exception as exc2:
                log.warning("xhtml2pdf 渲染失败，降级到 fpdf2: %s", exc2)
                # fpdf2 不支持 HTML，走 Markdown 降级路径
                raise ResumeRenderError(
                    f"PDF 渲染失败（weasyprint: {exc}, xhtml2pdf: {exc2}），"
                    "且 fpdf2 不支持结构化模板渲染"
                )

    if backend == "xhtml2pdf":
        try:
            return _html_to_pdf_xhtml2pdf(html)
        except Exception as exc:
            log.warning("xhtml2pdf 渲染失败: %s", exc)
            raise ResumeRenderError(f"PDF 渲染失败: {exc}")

    # fpdf2 不支持 HTML+CSS，无法渲染 Jinja2 模板
    raise ResumeRenderError(
        "当前 PDF 后端 fpdf2 不支持结构化模板渲染，请安装 weasyprint 或 xhtml2pdf"
    )


def _html_to_pdf_weasyprint(html: str) -> bytes:
    """使用 weasyprint 将 HTML 渲染为 PDF。"""
    from weasyprint import HTML as WeasyHTML

    pdf_bytes = WeasyHTML(string=html).write_pdf()
    return bytes(pdf_bytes)


def _html_to_pdf_xhtml2pdf(html: str) -> bytes:
    """使用 xhtml2pdf 将 HTML 渲染为 PDF。"""
    _ensure_fonts_registered()

    from xhtml2pdf import pisa

    output = io.BytesIO()
    result = pisa.pisaDocument(
        io.BytesIO(html.encode("utf-8")),
        output,
        encoding="utf-8",
    )

    if result.err:
        log.warning("xhtml2pdf 渲染有 %d 个警告", result.err)

    return output.getvalue()


# ---------------------------------------------------------------------------
# Markdown 渲染（降级路径，保留兼容性）
# ---------------------------------------------------------------------------

def render_markdown_to_pdf(markdown_content: str, template: str = "professional") -> bytes:
    """将 Markdown 渲染为 PDF 字节（降级路径）。

    自动选择最佳可用后端：
    1. weasyprint: Markdown → HTML + CSS → PDF（高质量，需 GTK）
    2. xhtml2pdf: Markdown → HTML + CSS → PDF（纯 Python，跨平台）
    3. fpdf2: Markdown → PDF（基础质量，直接渲染）

    Args:
        markdown_content: Markdown 格式的简历内容
        template: CSS 模板名称

    Returns:
        PDF 字节数据
    """
    # 先尝试结构化解析 + Jinja2 模板
    try:
        from resume_agent.resume_parser import parse_markdown_to_resume_data
        resume_data = parse_markdown_to_resume_data(markdown_content)
        if resume_data.has_content():
            return render_resume_data_to_pdf(resume_data, template)
    except Exception as exc:
        log.warning("结构化渲染失败，降级到 Markdown 渲染: %s", exc)

    # 降级到旧的 Markdown → HTML → PDF 路径
    backend = detect_pdf_backend()

    if backend == "weasyprint":
        try:
            return _render_md_weasyprint(markdown_content, template)
        except Exception as exc:
            log.warning("weasyprint 渲染失败，降级到 xhtml2pdf: %s", exc)
            try:
                return _render_md_xhtml2pdf(markdown_content, template)
            except Exception as exc2:
                log.warning("xhtml2pdf 渲染失败，降级到 fpdf2: %s", exc2)
                return _render_md_fpdf2(markdown_content, template)

    if backend == "xhtml2pdf":
        try:
            return _render_md_xhtml2pdf(markdown_content, template)
        except Exception as exc:
            log.warning("xhtml2pdf 渲染失败，降级到 fpdf2: %s", exc)
            return _render_md_fpdf2(markdown_content, template)

    return _render_md_fpdf2(markdown_content, template)


def _render_md_weasyprint(markdown_content: str, template: str) -> bytes:
    """使用 weasyprint 渲染 Markdown（降级路径）。"""
    html = _markdown_to_full_html(markdown_content, template)
    return _html_to_pdf_weasyprint(html)


def _render_md_xhtml2pdf(markdown_content: str, template: str) -> bytes:
    """使用 xhtml2pdf 渲染 Markdown（降级路径）。"""
    html = _markdown_to_full_html(markdown_content, template)
    return _html_to_pdf_xhtml2pdf(html)


def _render_md_fpdf2(markdown_content: str, template: str) -> bytes:
    """使用 fpdf2 渲染 PDF（原有实现，最后降级）。"""
    from resume_agent.render_pdf import render_markdown_to_pdf as fpdf2_render

    return fpdf2_render(markdown_content, template=template)


# ---------------------------------------------------------------------------
# 中文字体注册
# ---------------------------------------------------------------------------

def _find_chinese_ttf() -> tuple[str, Path] | None:
    """查找系统中可用的中文 TTF 字体。"""
    system = platform.system()
    if system == "Windows":
        search_dirs = [Path("C:/Windows/Fonts")]
    elif system == "Darwin":
        search_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    else:
        search_dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local" / "share" / "fonts",
        ]

    # 项目内置字体目录
    local_fonts = Path(__file__).parent / "templates" / "fonts"
    if local_fonts.exists():
        search_dirs.append(local_fonts)

    candidates = [
        ("SimHei", "simhei.ttf"),
        ("MicrosoftYaHei", "msyh.ttc"),
        ("NotoSansSC", "NotoSansSC-Regular.ttf"),
        ("WenQuanYiMicroHei", "wqy-microhei.ttc"),
        ("PingFangSC", "PingFang.ttc"),
    ]

    for name, filename in candidates:
        for font_dir in search_dirs:
            p = font_dir / filename
            if p.exists():
                return name, p
            for match in font_dir.rglob(filename):
                return name, match

    return None


def _ensure_fonts_registered() -> None:
    """确保中文字体已注册到 reportlab 和 xhtml2pdf（仅执行一次）。"""
    global _font_registered
    if _font_registered:
        return

    font_info = _find_chinese_ttf()
    if font_info is None:
        log.warning("未找到可用的中文字体 TTF 文件，PDF 中文可能显示异常")
        _font_registered = True
        return

    font_name, font_path = font_info

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # .ttc 文件需要指定 subfontIndex
        if font_path.suffix.lower() == ".ttc":
            pdfmetrics.registerFont(TTFont(font_name, str(font_path), subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

        # 向 xhtml2pdf 的 pisaContext 注册字体映射
        try:
            from xhtml2pdf.context import pisaContext

            _orig_init = pisaContext.__init__

            def _patched_init(self, *args, **kwargs):
                _orig_init(self, *args, **kwargs)
                self.fontList[font_name] = font_name
                self.fontList[font_name.lower()] = font_name
                self.fontList[font_name + "-Bold"] = font_name
                # 常见中文别名
                self.fontList["SimHei"] = font_name
                self.fontList["Microsoft YaHei"] = font_name
                self.fontList["PingFang SC"] = font_name
                self.fontList["Noto Sans SC"] = font_name

            pisaContext.__init__ = _patched_init
        except Exception as exc:
            log.debug("xhtml2pdf 字体映射注册失败: %s", exc)

        log.info("中文字体注册成功: %s (%s)", font_name, font_path)
    except Exception as exc:
        log.warning("中文字体注册失败: %s", exc)

    _font_registered = True


# ---------------------------------------------------------------------------
# HTML + CSS 公共构建（Markdown 降级路径使用）
# ---------------------------------------------------------------------------

def _load_css_template(template: str) -> str:
    """加载 CSS 模板内容（Markdown 降级路径使用）。"""
    css_path = Path(__file__).parent / "templates" / f"{template}.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    fallback = Path(__file__).parent / "templates" / "professional.css"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return ""


def _get_font_family_css() -> str:
    """生成 CSS font-family 声明（确保中文显示）。"""
    font_info = _find_chinese_ttf()
    if font_info:
        font_name = font_info[0]
        return f'''
*, p, li, h1, h2, h3, h4, h5, h6, td, th, span, div, strong, em, a {{
    font-family: "{font_name}", "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans SC", sans-serif !important;
}}
'''
    return ""


def _markdown_to_full_html(markdown_content: str, template: str) -> str:
    """将 Markdown 转为完整的 HTML 文档（含 CSS 模板，Markdown 降级路径使用）。"""
    import markdown as md_lib

    html_body = md_lib.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    css_content = _load_css_template(template)
    font_css = _get_font_family_css()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
{font_css}
{css_content}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
