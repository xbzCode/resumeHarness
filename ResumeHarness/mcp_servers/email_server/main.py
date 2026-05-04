"""邮件发送 HTTP MCP 服务。

提供 SMTP 邮件发送能力，作为独立 HTTP 服务运行，
主进程通过 MCP 协议调用。

启动方式：
    python main.py

默认监听 localhost:9101。

环境变量配置：
    SMTP_HOST     — SMTP 服务器地址（必填）
    SMTP_PORT     — SMTP 端口（默认 587）
    SMTP_USER     — SMTP 用户名（必填）
    SMTP_PASSWORD — SMTP 密码（必填）
    SMTP_FROM     — 发件人地址（默认同 SMTP_USER）
    SMTP_USE_TLS  — 是否使用 TLS（默认 true）
"""

from __future__ import annotations

import base64
import logging
import os
import smtplib
import traceback
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="Email MCP Server", version="1.0.0")


# ---------------------------------------------------------------------------
# SMTP 配置
# ---------------------------------------------------------------------------

class SmtpConfig(BaseModel):
    """SMTP 配置。"""

    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    use_tls: bool = True


def _load_smtp_config() -> SmtpConfig:
    """从环境变量加载 SMTP 配置。"""
    host = os.environ.get("SMTP_HOST", "")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    from_addr = os.environ.get("SMTP_FROM", user)
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    return SmtpConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        from_addr=from_addr,
        use_tls=use_tls,
    )


_smtp_config: SmtpConfig | None = None


def _get_smtp_config() -> SmtpConfig:
    """获取 SMTP 配置（懒加载）。"""
    global _smtp_config
    if _smtp_config is None:
        _smtp_config = _load_smtp_config()
    return _smtp_config


# ---------------------------------------------------------------------------
# MCP 工具定义
# ---------------------------------------------------------------------------

class SendInput(BaseModel):
    """邮件发送工具输入。"""

    to: str = Field(description="收件人邮箱地址，多个用逗号分隔")
    subject: str = Field(description="邮件主题")
    body: str = Field(description="邮件正文（支持 HTML）")
    cc: str = Field(default="", description="抄送邮箱，多个用逗号分隔")
    bcc: str = Field(default="", description="密送邮箱，多个用逗号分隔")
    attachments: list[dict[str, str]] = Field(
        default_factory=list,
        description="附件列表，每项包含 name（文件名）和 content（base64 编码内容）",
    )


# ---------------------------------------------------------------------------
# MCP 协议端点
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, Any]:
    """健康检查。"""
    config = _get_smtp_config()
    smtp_configured = bool(config.host and config.user and config.password)
    return {
        "status": "ok",
        "smtp_configured": smtp_configured,
    }


@app.post("/tools/list")
async def tools_list() -> dict[str, Any]:
    """列出可用工具（MCP 协议）。"""
    return {
        "tools": [
            {
                "name": "send",
                "description": "发送邮件，支持 HTML 正文和附件",
                "inputSchema": SendInput.model_json_schema(),
                "annotations": {
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "category": "邮件发送",
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

    if tool_name == "send":
        return await _handle_send(arguments)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "isError": True,
                "errorMessage": f"Unknown tool: {tool_name}",
            },
        )


async def _handle_send(arguments: dict[str, Any]) -> JSONResponse:
    """处理邮件发送请求。"""
    config = _get_smtp_config()

    if not config.host or not config.user or not config.password:
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": "SMTP 未配置，请设置 SMTP_HOST、SMTP_USER、SMTP_PASSWORD 环境变量",
            }
        )

    try:
        to_addr = arguments.get("to", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        cc = arguments.get("cc", "")
        bcc = arguments.get("bcc", "")
        attachments = arguments.get("attachments", [])

        if not to_addr:
            return JSONResponse(
                content={
                    "isError": True,
                    "errorMessage": "收件人地址不能为空",
                }
            )

        if not subject:
            return JSONResponse(
                content={
                    "isError": True,
                    "errorMessage": "邮件主题不能为空",
                }
            )

        # 构建邮件
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("Resume Agent", config.from_addr or config.user))
        msg["To"] = to_addr
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc

        # 添加 HTML 正文
        html_part = MIMEText(body, "html", "utf-8")
        msg.attach(html_part)

        # 添加附件
        for attachment in attachments:
            att_name = attachment.get("name", "attachment")
            att_content_b64 = attachment.get("content", "")
            if not att_content_b64:
                continue

            try:
                att_bytes = base64.b64decode(att_content_b64)
                att_part = MIMEBase("application", "octet-stream")
                att_part.set_payload(att_bytes)
                att_part.add_header(
                    "Content-Disposition",
                    f"attachment; filename*=UTF-8''{_encode_filename(att_name)}",
                )
                msg.attach(att_part)
            except Exception as exc:
                logger.warning("添加附件失败 %s: %s", att_name, exc)

        # 收件人列表
        all_recipients = [addr.strip() for addr in to_addr.split(",")]
        if cc:
            all_recipients.extend(addr.strip() for addr in cc.split(","))
        if bcc:
            all_recipients.extend(addr.strip() for addr in bcc.split(","))

        # 发送邮件
        _send_smtp(config, msg, all_recipients)

        return JSONResponse(
            content={
                "content": [
                    {
                        "type": "text",
                        "text": f"邮件发送成功：{to_addr}",
                    }
                ],
                "isError": False,
            }
        )

    except Exception as exc:
        logger.error("邮件发送失败: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            content={
                "isError": True,
                "errorMessage": f"邮件发送失败: {exc}",
            }
        )


def _encode_filename(name: str) -> str:
    """对文件名进行 RFC 2231 编码。"""
    from urllib.parse import quote
    return quote(name, safe="")


def _send_smtp(
    config: SmtpConfig,
    msg: MIMEMultipart,
    recipients: list[str],
) -> None:
    """通过 SMTP 发送邮件。"""
    if config.use_tls and config.port == 587:
        # STARTTLS
        server = smtplib.SMTP(config.host, config.port, timeout=30)
        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.user, config.password)
            server.sendmail(config.from_addr or config.user, recipients, msg.as_string())
        finally:
            server.quit()
    elif config.port == 465:
        # SSL
        server = smtplib.SMTP_SSL(config.host, config.port, timeout=30)
        try:
            server.login(config.user, config.password)
            server.sendmail(config.from_addr or config.user, recipients, msg.as_string())
        finally:
            server.quit()
    else:
        # 无加密
        server = smtplib.SMTP(config.host, config.port, timeout=30)
        try:
            server.login(config.user, config.password)
            server.sendmail(config.from_addr or config.user, recipients, msg.as_string())
        finally:
            server.quit()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    """启动 Email MCP 服务。"""
    host = os.environ.get("EMAIL_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("EMAIL_MCP_PORT", "9101"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 检查 SMTP 配置
    config = _load_smtp_config()
    if config.host and config.user:
        logger.info("SMTP 配置: %s:%d (user=%s)", config.host, config.port, config.user)
    else:
        logger.warning("SMTP 未完整配置，邮件发送功能不可用")

    logger.info("启动 Email MCP 服务: %s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
