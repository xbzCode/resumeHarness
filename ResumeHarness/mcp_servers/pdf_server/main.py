"""PDF 转换 HTTP MCP 服务。

提供 HTML → PDF 转换能力，作为独立 HTTP 服务运行，
主进程通过 MCP 协议调用，隔离 weasyprint 渲染。

启动方式：
    python main.py

默认监听 localhost:9100。
"""

from __future__ import annotations

import base64
import logging
import os
import traceback
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="PDF MCP Server", version="1.0.0")


# ---------------------------------------------------------------------------
# MCP 工具定义
# ---------------------------------------------------------------------------

class ConvertInput(BaseModel):
    """PDF 转换工具输入。"""

    html: str = Field(description="HTML 内容")
    template: str = Field(default="professional", description="模板名称")


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
                "name": "convert",
                "description": "将 HTML 内容转换为 PDF 文件，返回 base64 编码的 PDF 数据",
                "inputSchema": ConvertInput.model_json_schema(),
            }
        ]
    }


@app.post("/tools/call")
async def tools_call(request: Request) -> JSONResponse:
    """调用工具（MCP 协议）。"""
    body = await request.json()
    tool_name = body.get("name", "")
    arguments = body.get("arguments", {})

    if tool_name == "convert":
        return await _handle_convert(arguments)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "isError": True,
                "errorMessage": f"Unknown tool: {tool_name}",
            },
        )


async def _handle_convert(arguments: dict[str, Any]) -> JSONResponse:
    """处理 PDF 转换请求。"""
    try:
        html_content = arguments.get("html", "")
        template_name = arguments.get("template", "professional")

        if not html_content:
            return JSONResponse(
                content={
                    "isError": True,
                    "errorMessage": "html 参数不能为空",
                }
            )

        # 尝试使用 weasyprint
        pdf_bytes = _render_pdf_with_weasyprint(html_content, template_name)

        if pdf_bytes is None:
            return JSONResponse(
                content={
                    "isError": True,
                    "errorMessage": "PDF 渲染失败，请检查 weasyprint 是否正确安装",
                }
            )

        # 返回 base64 编码的 PDF
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")

        return JSONResponse(
            content={
                "content": [
                    {
                        "type": "text",
                        "text": pdf_base64,
                    }
                ],
                "isError": False,
            }
        )

    except Exception as exc:
        logger.error("PDF 转换失败: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": f"PDF 转换失败: {exc}",
            }
        )


def _render_pdf_with_weasyprint(html_content: str, template_name: str) -> bytes | None:
    """使用 weasyprint 渲染 PDF。"""
    try:
        from weasyprint import HTML

        # 添加打印样式
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: A4;
    margin: 0;
}}
body {{
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
</style>
</head>
<body>
{html_content}
</body>
</html>"""

        html_doc = HTML(string=styled_html)
        pdf_bytes = html_doc.write_pdf()
        return pdf_bytes

    except ImportError:
        logger.warning("weasyprint 未安装，PDF 转换不可用")
        return None
    except Exception as exc:
        logger.error("weasyprint 渲染失败: %s", exc)
        return None


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    """启动 PDF MCP 服务。"""
    host = os.environ.get("PDF_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("PDF_MCP_PORT", "9100"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("启动 PDF MCP 服务: %s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
