# PDF 转换 MCP 服务

基于 weasyprint 的 PDF 转换 HTTP MCP 服务。

## 安装

```bash
pip install -r requirements.txt
```

## 启动

```bash
python main.py
```

默认监听 `localhost:9100`，可通过环境变量 `PDF_MCP_HOST` 和 `PDF_MCP_PORT` 配置。

## MCP 工具

### convert

将 HTML 内容转换为 PDF。

**输入参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| html | string | 是 | HTML 内容 |
| template | string | 否 | 模板名称（professional/academic/creative），默认 professional |

**输出：**

PDF 文件的 base64 编码字符串。

## API 端点

- `GET  /health` — 健康检查
- `POST /tools/list` — 列出可用工具
- `POST /tools/call` — 调用工具
