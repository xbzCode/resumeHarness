# 邮件发送 MCP 服务

基于 SMTP 的邮件发送 HTTP MCP 服务。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

通过环境变量配置 SMTP：

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-password
SMTP_FROM=your@email.com
```

## 启动

```bash
python main.py
```

默认监听 `localhost:9101`，可通过环境变量 `EMAIL_MCP_HOST` 和 `EMAIL_MCP_PORT` 配置。

## MCP 工具

### send

发送邮件（支持附件）。

**输入参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| to | string | 是 | 收件人邮箱 |
| subject | string | 是 | 邮件主题 |
| body | string | 是 | 邮件正文（支持 HTML） |
| cc | string | 否 | 抄送（多个用逗号分隔） |
| bcc | string | 否 | 密送（多个用逗号分隔） |
| attachments | array | 否 | 附件列表，每项包含 name 和 content（base64） |

## API 端点

- `GET  /health` — 健康检查
- `POST /tools/list` — 列出可用工具
- `POST /tools/call` — 调用工具
