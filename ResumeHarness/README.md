# Resume Agent

简历智能体 - 基于 OpenHarness 裁剪的简历优化 Agent，接入 DeepSeek API。

## 快速开始

### 1. 创建并激活虚拟环境

```bash
cd ResumeHarness

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
```

> 后续所有命令均需在激活的虚拟环境中执行。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

开发模式额外依赖：

```bash
pip install -r requirements.txt pytest pytest-asyncio ruff
```

### 3. 配置 DeepSeek API

复制项目根目录下的 `.env.example` 文件为 `.env`，并填写你的 API Key：

```bash
# 复制配置模板
cp .env.example .env    # macOS / Linux
copy .env.example .env  # Windows
```

然后编辑 `.env` 文件，填入你的配置：

```ini
# 必填：DeepSeek API Key
DEEPSEEK_API_KEY=sk-your-api-key-here

# 可选：自定义 Base URL（默认 https://api.deepseek.com）
# DEEPSEEK_BASE_URL=https://api.deepseek.com

# 可选：自定义模型（默认 deepseek-chat）
# DEEPSEEK_MODEL=deepseek-chat
```

> 配置优先级：`.env` 文件 > 系统环境变量 > `~/.resume_agent/settings.json` > 默认值

### 4. 启动服务

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

或使用项目入口：

```bash
pip install -e .
resume-agent
```

启动成功后访问：

- 前端页面：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 5. 运行测试

```bash
python -m pytest tests/ -v
```

## 配置项参考

| 配置项 | .env 变量 | 默认值 | 说明 |
|--------|-----------|--------|------|
| api_key | DEEPSEEK_API_KEY | - | DeepSeek API Key（必填） |
| api_keys | - | [] | 多 Key 轮询列表（settings.json） |
| base_url | DEEPSEEK_BASE_URL | https://api.deepseek.com | API Base URL |
| model | DEEPSEEK_MODEL | deepseek-chat | 模型名称 |
| timeout | - | 30.0 | 请求超时（秒） |
| max_tokens | - | 4096 | 最大生成 token 数 |
| max_turns | - | 200 | 最大工具调用轮次 |
| max_sessions | - | 20 | 最大并发会话数 |
| idle_timeout | - | 1800 | 会话空闲超时（秒） |
| default_user_id | DEFAULT_USER_ID | dev_user | 开发模式默认用户 ID |
| data_root | RESUME_AGENT_DATA_ROOT | ~/.resume_agent | 数据根目录 |

## 项目结构

```
ResumeHarness/
├── .env.example              # 环境变量配置模板
├── backend/                  # FastAPI 后端
│   ├── app.py               # 应用入口 + 生命周期
│   ├── routes/chat.py       # SSE 流式对话端点
│   └── middleware/           # 中间件（预留）
├── resume_agent/             # 核心 Agent 包
│   ├── api/                  # API 客户端（OpenAI 兼容协议）
│   │   ├── client.py        # 协议 + 请求/响应类型
│   │   ├── openai_client.py # DeepSeek/OpenAI 客户端
│   │   ├── errors.py        # API 错误类型
│   │   └── usage.py         # Token 用量统计
│   ├── engine/               # 对话引擎
│   │   ├── query_engine.py  # QueryEngine 高层封装
│   │   ├── query.py         # 核心工具调用循环
│   │   ├── messages.py      # 消息/内容块模型
│   │   ├── stream_events.py # 流式事件类型
│   │   └── cost_tracker.py  # 费用累计
│   ├── config/               # 配置管理
│   │   └── settings.py      # 全局配置加载
│   ├── permissions/          # 权限检查
│   │   ├── checker.py       # PermissionChecker（P0: AUTO）
│   │   └── modes.py         # PermissionMode 枚举
│   ├── hooks/                # Hook 系统（P0: 空实现）
│   │   ├── executor.py
│   │   └── loader.py
│   ├── tools/                # 工具集
│   │   ├── base.py          # BaseTool / ToolRegistry
│   │   ├── memory_write.py  # 记忆写入
│   │   ├── web_fetch.py     # 网页抓取
│   │   └── skill_loader.py  # 技能加载
│   ├── memory/               # 用户记忆
│   ├── prompts/              # 系统提示词
│   ├── models/               # 数据模型
│   ├── services/             # 服务层
│   ├── channels/             # 通道层（预留）
│   ├── templates/            # 简历模板 CSS
│   ├── runtime.py            # RuntimeBundle 构建
│   ├── session_pool.py       # 多租户会话池
│   ├── api_key_pool.py       # 多 Key 轮询
│   └── exceptions.py         # 统一错误码
├── frontend/                 # 极简前端验证页
│   └── index.html
├── tests/                    # 测试
├── pyproject.toml
└── requirements.txt
```
