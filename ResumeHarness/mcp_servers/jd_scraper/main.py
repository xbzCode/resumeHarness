"""JD 抓取 HTTP MCP 服务。

提供招聘网站 JD 描述抓取能力，支持主流招聘网站自动解析。
作为独立 HTTP 服务运行，主进程通过 MCP 协议调用。

支持网站：
- Boss直聘 (zhipin.com)
- 拉勾网 (lagou.com)
- 猎聘 (liepin.com)
- 前程无忧 (51job.com)
- 智联招聘 (zhaopin.com)
- 通用 HTTP 页面（非以上网站时自动降级）

启动方式：
    python main.py

默认监听 localhost:9102。
"""

from __future__ import annotations

import logging
import os
import re
import traceback
from typing import Any
from urllib.parse import urlsplit

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="JD Scraper MCP Server", version="1.0.0")

# HTTP 客户端（连接复用）
_http_client: httpx.AsyncClient | None = None

# 抓取超时
_SCRAPE_TIMEOUT = 15.0
# 内容最大长度
_MAX_CONTENT_LENGTH = 8000


def _get_http_client() -> httpx.AsyncClient:
    """获取或创建 HTTP 客户端。"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(_SCRAPE_TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
    return _http_client


# ---------------------------------------------------------------------------
# MCP 工具定义
# ---------------------------------------------------------------------------

class ScrapeJdInput(BaseModel):
    """JD 抓取工具输入。"""

    url: str = Field(description="招聘页面的 URL")
    max_length: int = Field(default=6000, description="返回内容的最大字符数")


# ---------------------------------------------------------------------------
# JD 解析器
# ---------------------------------------------------------------------------

def _detect_site(url: str) -> str:
    """检测 URL 对应的招聘网站类型。"""
    domain = urlsplit(url).netloc.lower()
    if "zhipin.com" in domain:
        return "boss"
    elif "lagou.com" in domain:
        return "lagou"
    elif "liepin.com" in domain:
        return "liepin"
    elif "51job.com" in domain:
        return "51job"
    elif "zhaopin.com" in domain:
        return "zhaopin"
    return "generic"


def _extract_with_regex(html: str, site: str) -> dict[str, Any]:
    """使用正则从 HTML 提取 JD 信息。"""
    result: dict[str, Any] = {
        "title": "",
        "company": "",
        "location": "",
        "salary": "",
        "description": "",
    }

    if site == "boss":
        # Boss直聘
        title_m = re.search(r'<h1[^>]*class="name"[^>]*>(.*?)</h1>', html, re.S)
        if title_m:
            result["title"] = _clean_text(title_m.group(1))
        salary_m = re.search(r'<span[^>]*class="salary"[^>]*>(.*?)</span>', html, re.S)
        if salary_m:
            result["salary"] = _clean_text(salary_m.group(1))
        # Boss 直聘的 JD 内容在 .job-detail-section 或 .text 类下
        desc_m = re.search(
            r'<div[^>]*class="[^"]*job-detail[^"]*"[^>]*>(.*?)</div>',
            html, re.S,
        )
        if not desc_m:
            desc_m = re.search(
                r'<div[^>]*class="[^"]*text[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html, re.S,
            )
        if desc_m:
            result["description"] = _html_to_text(desc_m.group(1))

    elif site == "lagou":
        # 拉勾网
        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if title_m:
            result["title"] = _clean_text(title_m.group(1))
        salary_m = re.search(r'<span[^>]*class="[^"]*salary[^"]*"[^>]*>(.*?)</span>', html, re.S)
        if salary_m:
            result["salary"] = _clean_text(salary_m.group(1))
        desc_m = re.search(
            r'<dd[^>]*class="[^"]*job_bt[^"]*"[^>]*>(.*?)</dd>',
            html, re.S,
        )
        if desc_m:
            result["description"] = _html_to_text(desc_m.group(1))

    elif site == "liepin":
        # 猎聘
        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if title_m:
            result["title"] = _clean_text(title_m.group(1))
        salary_m = re.search(
            r'<span[^>]*class="[^"]*salary[^"]*"[^>]*>(.*?)</span>',
            html, re.S,
        )
        if salary_m:
            result["salary"] = _clean_text(salary_m.group(1))
        desc_m = re.search(
            r'<div[^>]*class="[^"]*job-description[^"]*"[^>]*>(.*?)</div>',
            html, re.S,
        )
        if desc_m:
            result["description"] = _html_to_text(desc_m.group(1))

    elif site in ("51job", "zhaopin"):
        # 前程无忧 / 智联招聘
        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if not title_m:
            title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
        if title_m:
            result["title"] = _clean_text(title_m.group(1))
        # 尝试提取描述
        desc_m = re.search(
            r'<div[^>]*class="[^"]*(?:descri|detail|content)[^"]*"[^>]*>(.*?)</div>',
            html, re.S | re.I,
        )
        if desc_m:
            result["description"] = _html_to_text(desc_m.group(1))

    # 通用降级：如果以上解析失败，提取 <body> 或 <title> 中的文本
    if not result["description"]:
        result["description"] = _generic_extract(html)

    if not result["title"]:
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
        if title_m:
            result["title"] = _clean_text(title_m.group(1))

    return result


def _generic_extract(html: str) -> str:
    """通用 HTML 正文提取（降级方案）。"""
    # 移除 script、style 标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.S | re.I)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S | re.I)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.S | re.I)
    text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.S | re.I)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.S | re.I)

    # 尝试提取 body 内容
    body_m = re.search(r'<body[^>]*>(.*?)</body>', text, re.S | re.I)
    if body_m:
        text = body_m.group(1)

    return _html_to_text(text)


def _html_to_text(html: str) -> str:
    """将 HTML 转换为纯文本。"""
    # 替换常见块级标签为换行
    text = re.sub(r'<br\s*/?\s*>', '\n', html, flags=re.I)
    text = re.sub(r'</(p|div|li|h[1-6]|tr|dd|dt)>', '\n', text, flags=re.I)
    # 移除所有剩余标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码 HTML 实体
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    # 清理空白
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    return '\n'.join(lines)


def _clean_text(text: str) -> str:
    """清理 HTML 标签和多余空白。"""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    return text.strip()


def _format_jd_result(data: dict[str, Any], max_length: int) -> str:
    """将提取的 JD 信息格式化为 Markdown 文本。"""
    parts: list[str] = []

    if data.get("title"):
        parts.append(f"# {data['title']}")
    if data.get("company"):
        parts.append(f"**公司**：{data['company']}")
    if data.get("salary"):
        parts.append(f"**薪资**：{data['salary']}")
    if data.get("location"):
        parts.append(f"**地点**：{data['location']}")

    if data.get("description"):
        parts.append("")
        parts.append("## 职位描述")
        parts.append(data["description"])

    text = "\n".join(parts)

    # 截断
    if len(text) > max_length:
        text = text[:max_length] + "\n\n...(内容已截断)"

    return text


# ---------------------------------------------------------------------------
# MCP 协议端点
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


@app.post("/tools/list")
async def tools_list() -> dict[str, Any]:
    """列出可用工具（MCP 协议）。"""
    return {
        "tools": [
            {
                "name": "scrape_jd",
                "description": (
                    "抓取招聘网站的职位描述（JD），自动解析岗位名称、薪资、要求等信息。"
                    "支持 Boss直聘、拉勾网、猎聘、前程无忧、智联招聘等主流招聘网站。"
                    "当用户提供招聘链接时，应使用此工具获取详细的岗位描述。"
                ),
                "inputSchema": ScrapeJdInput.model_json_schema(),
                "annotations": {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "category": "网络抓取",
                    "timeout_ms": 30000,
                },
            }
        ]
    }


@app.post("/tools/call")
async def tools_call(request: Request) -> JSONResponse:
    """调用工具（MCP 协议）。"""
    body = await request.json()
    tool_name = body.get("name", "")
    arguments = body.get("arguments", {})

    if tool_name == "scrape_jd":
        return await _handle_scrape_jd(arguments)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "isError": True,
                "errorMessage": f"Unknown tool: {tool_name}",
            },
        )


async def _handle_scrape_jd(arguments: dict[str, Any]) -> JSONResponse:
    """处理 JD 抓取请求。"""
    url = arguments.get("url", "")
    max_length = min(arguments.get("max_length", 6000), _MAX_CONTENT_LENGTH)

    if not url:
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": "url 参数不能为空",
            }
        )

    # 验证 URL 协议
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": "仅支持 http/https 协议的 URL",
            }
        )

    try:
        client = _get_http_client()
        resp = await client.get(url)
        resp.raise_for_status()

        html = resp.text
        site = _detect_site(url)

        # 解析 JD 信息
        data = _extract_with_regex(html, site)
        result_text = _format_jd_result(data, max_length)

        if not result_text.strip():
            return JSONResponse(
                content={
                    "isError": True,
                    "errorMessage": "未能从页面中提取到有效的职位描述信息",
                }
            )

        return JSONResponse(
            content={
                "content": [
                    {
                        "type": "text",
                        "text": result_text,
                    }
                ],
                "isError": False,
            }
        )

    except httpx.TimeoutException:
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": f"请求超时，请检查 URL 是否可访问: {url}",
            }
        )
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": f"HTTP 请求失败 (状态码 {exc.response.status_code}): {url}",
            }
        )
    except Exception as exc:
        logger.error("JD 抓取失败: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": f"JD 抓取失败: {exc}",
            }
        )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event() -> None:
    """关闭 HTTP 客户端。"""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def main() -> None:
    """启动 JD 抓取 MCP 服务。"""
    host = os.environ.get("JD_SCRAPER_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("JD_SCRAPER_MCP_PORT", "9102"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("启动 JD 抓取 MCP 服务: %s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
