# JD 抓取 MCP 服务

招聘网站职位描述（JD）自动抓取服务，作为独立 HTTP MCP 服务运行。

## 功能

- 抓取招聘页面的职位描述，自动解析岗位名称、薪资、要求等信息
- 支持主流招聘网站：Boss直聘、拉勾网、猎聘、前程无忧、智联招聘
- 非支持网站自动降级为通用 HTML 正文提取

## 启动

```bash
pip install -r requirements.txt
python main.py
```

默认监听 `localhost:9102`，可通过环境变量配置：

- `JD_SCRAPER_MCP_HOST` — 监听地址（默认 `127.0.0.1`）
- `JD_SCRAPER_MCP_PORT` — 监听端口（默认 `9102`）

## MCP 协议

### 工具列表

| 工具 | 说明 |
|------|------|
| `scrape_jd` | 抓取招聘网站 JD 描述 |

### scrape_jd 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 招聘页面 URL |
| `max_length` | integer | 否 | 返回内容最大字符数（默认 6000，上限 8000） |

### 示例

```bash
# 列出工具
curl http://localhost:9102/tools/list

# 抓取 JD
curl -X POST http://localhost:9102/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "scrape_jd", "arguments": {"url": "https://www.zhipin.com/job_detail/xxx.html"}}'
```
