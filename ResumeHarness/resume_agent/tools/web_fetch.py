"""网页内容抓取工具，供 LLM 在对话中主动调用。"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from resume_agent.tools.base import BaseTool, ToolExecutionContext, ToolResult

log = logging.getLogger(__name__)

# URL 缓存（5 分钟有效）
_url_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 分钟


class WebFetchInput(BaseModel):
    """web_fetch 工具输入。"""

    url: str = Field(description="要抓取的网页 URL")
    max_length: int = Field(default=4000, description="返回内容的最大字符数，默认 4000")


class WebFetchTool(BaseTool):
    """网页内容抓取工具，供 LLM 在对话中主动调用。

    当用户提供招聘链接或需要获取网页内容时，调用此工具。
    抓取结果将作为上下文参与后续简历生成。
    """

    name = "web_fetch"
    description = (
        "抓取指定 URL 的网页内容，提取纯文本。"
        "当用户提供招聘链接或需要获取网页内容时，调用此工具。"
        "抓取结果将作为上下文参与后续简历生成。"
    )
    input_model = WebFetchInput

    async def execute(self, arguments: WebFetchInput, context: ToolExecutionContext) -> ToolResult:
        """执行网页抓取。"""
        url = arguments.url.strip()

        # 校验协议
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ToolResult(
                output=f"不支持的协议: {parsed.scheme}，仅允许 HTTP/HTTPS",
                is_error=True,
            )

        # 检查缓存
        if url in _url_cache:
            cached_content, cached_time = _url_cache[url]
            if time.monotonic() - cached_time < _CACHE_TTL:
                return ToolResult(output=cached_content[:arguments.max_length])

        # 抓取网页
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException:
            return ToolResult(output=f"抓取超时: {url}", is_error=True)
        except httpx.HTTPStatusError as exc:
            return ToolResult(output=f"HTTP 错误 {exc.response.status_code}: {url}", is_error=True)
        except Exception as exc:
            return ToolResult(output=f"抓取失败: {exc}", is_error=True)

        # 提取正文
        content = _extract_text(response.text)

        # 缓存结果
        _url_cache[url] = (content, time.monotonic())

        # 截断
        if len(content) > arguments.max_length:
            content = content[:arguments.max_length] + "\n\n... (内容已截断)"

        return ToolResult(output=content)

    def is_read_only(self, arguments: WebFetchInput) -> bool:
        return True


def _extract_text(html: str) -> str:
    """从 HTML 中提取正文文本。

    优先使用 readability-lxml 提取正文；若未安装则回退到正则提取。
    """
    # 优先使用 readability-lxml
    try:
        from readability import Document
        doc = Document(html)
        summary_html = doc.summary()
        # 去除 HTML 标签，保留纯文本
        import re
        text = re.sub(r"<[^>]+>", " ", summary_html)
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except ImportError:
        pass

    # 回退：简易正则提取
    import re

    # 去除 script/style 标签
    text = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # 尝试提取 <article> 或 <main> 标签内容
    m = re.search(r"<(?:article|main)[^>]*>(.*?)</(?:article|main)>", html, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1)
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)
    # 解码常见 HTML 实体
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    # 压缩空白
    text = re.sub(r"\s+", " ", text).strip()
    return text
