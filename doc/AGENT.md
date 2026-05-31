# Mylody 项目 AI Agent 快速指南

本文件为 AI Agent 提供项目快速概览，无需每次读取整个项目结构。

## 项目概述

**Mylody** 是一个 Windows 桌面音乐乐评 AI Agent，主要功能：

- **自动监听**：通过 Windows SMTC API 实时检测当前播放的音乐（支持 Spotify、网易云、Apple Music 等）
- **AI 乐评生成**：调用 Claude / OpenAI 生成专业中文乐评，包含情感分析、乐理解析、创作背景等
- **本地缓存**：SQLite 存储，同一首歌只请求一次 AI，后续直接读取缓存
- **Web 界面**：浏览器打开 `http://localhost:5800` 查看乐评
- **系统托盘**：Windows 系统托盘图标，支持后台运行

## 技术栈

### 后端
- **语言**：Python 3.11+
- **Web 框架**：FastAPI + Uvicorn
- **AI 集成**：
  - Anthropic Claude（默认）
  - OpenAI GPT
  - 自定义 OpenAI 兼容接口（DeepSeek、通义千问等）
- **数据库**：SQLite（通过 aiosqlite）
- **Windows 集成**：`winsdk` 库访问 Windows Media Control API
- **系统托盘**：`pystray` + `Pillow`

### 前端
- **技术**：原生 HTML + CSS + JavaScript（无框架）
- **特性**：极光背景动画、响应式设计、骨架屏加载

### 开发工具
- **测试**：pytest + pytest-asyncio
- **配置管理**：PyYAML

## 目录结构

```
d:\Mylody/
├── mylody/                    # 后端 Python 包
│   ├── ai/                    # AI 请求模块
│   │   ├── client.py          # AI 客户端，组装 Prompt → 调用 Provider → 解析 JSON
│   │   ├── prompt.py          # Prompt 模板
│   │   ├── provider_base.py   # AI Provider 基类
│   │   ├── provider_anthropic.py  # Anthropic Claude 实现
│   │   └── provider_openai.py     # OpenAI 实现
│   ├── cache/                 # SQLite 缓存管理
│   │   ├── db.py              # 数据库操作
│   │   ├── key.py             # 缓存键生成
│   │   └── manager.py         # 缓存管理器
│   ├── listener/              # Windows 媒体会话监听
│   │   ├── media_session.py   # WinRT 媒体会话封装
│   │   └── debounce.py        # 防抖处理
│   ├── server/                # FastAPI 路由
│   │   ├── app.py             # 应用工厂
│   │   ├── routes_status.py   # 状态 API
│   │   ├── routes_review.py   # 乐评 API
│   │   └── routes_config.py   # 配置 API
│   ├── utils/                 # 工具函数
│   │   ├── paths.py           # 路径工具
│   │   └── sanitize.py        # 文本清理
│   ├── config.py              # 配置管理
│   ├── config_defaults.py     # 默认配置
│   ├── logger.py              # 日志配置
│   ├── tray.py                # 系统托盘
│   └── types.py               # 类型定义（MediaInfo, ReviewData）
├── web/                       # 前端静态文件
│   ├── index.html             # 主页面
│   ├── css/                   # 样式文件（模块化）
│   └── js/                    # JavaScript 模块
├── tests/                     # 测试文件
├── doc/                       # 文档目录
├── img/                       # 图片资源
├── main.py                    # 入口文件
├── requirements.txt           # Python 依赖
├── config.example.yaml        # 配置示例
└── .gitignore                 # Git 忽略文件
```

## 关键文件说明

### 入口和配置
- **main.py**：应用入口，启动 FastAPI 服务和媒体监听
- **mylody/config.py**：配置管理，从 `~/.mylody/config.yaml` 加载配置
- **config.example.yaml**：配置示例，包含所有可配置项

### 核心模块
- **mylody/ai/client.py**：AI 客户端，负责组装 Prompt、调用 Provider、解析响应
- **mylody/listener/media_session.py**：Windows 媒体会话管理，获取当前播放信息
- **mylody/cache/manager.py**：缓存管理，SQLite 存储乐评数据
- **mylody/server/app.py**：FastAPI 应用工厂，注册路由和静态文件

### 类型定义
- **mylody/types.py**：定义 `MediaInfo`（媒体信息）和 `ReviewData`（乐评数据）数据类

## 开发指南

### 环境要求
- Windows 10/11（需要 Windows Media Control API）
- Python 3.11+（推荐 3.11，兼容 3.12/3.13）
- 网络连接（调用 AI API）

### 安装步骤

```bash
# 1. 创建虚拟环境
py -3.11 -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
# 首次运行会自动生成 ~/.mylody/config.yaml，编辑填写 API Key
```

### 配置文件

配置文件位于 `~/.mylody/config.yaml`，主要配置项：

```yaml
ai:
  provider: "anthropic"          # 可选: anthropic | openai | custom
  api_key: "YOUR_API_KEY"        # API Key
  model: "claude-sonnet-4-20250514"  # 模型名称
  base_url: ""                   # 仅 custom provider 需要填写
  timeout_seconds: 15            # 请求超时时间
  max_retries: 2                 # 失败重试次数

listener:
  poll_interval_seconds: 2       # 检测频率
  debounce_seconds: 3            # 防抖时间
  excluded_apps: []              # 排除的应用

cache:
  enabled: true
  cache_ttl_days: 0              # 0 = 永不过期
  db_path: ""                    # 留空使用默认路径

server:
  host: "127.0.0.1"
  port: 5800

logging:
  level: "INFO"                  # DEBUG | INFO | WARNING | ERROR
```

### 运行命令

```bash
# 启动服务
python main.py

# 指定端口
python main.py --port 8080

# 指定配置文件
python main.py --config ./my.yaml

# 禁用系统托盘
python main.py --no-tray
```

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_ai_client.py

# 运行带详细输出
pytest -v
```

## API 端点

### 状态 API
- **GET /api/status**：获取服务状态和当前播放信息
  - 返回：`running`, `current_track`, `uptime_seconds`, `is_generating`

### 乐评 API
- **GET /api/review/current**：获取当前播放歌曲的乐评
  - 返回：`status`, `track`, `review`
- **POST /api/review/refresh**：强制刷新当前乐评（跳过缓存）
  - 返回：`status`, `review`
- **GET /api/cache/stats**：获取缓存统计信息
  - 返回：`status`, `data`

### 静态文件
- **GET /**：Web 界面（`web/index.html`）

## 架构说明

### 数据流
1. **媒体监听**：`MediaListener` 轮询 Windows SMTC API 获取当前播放信息
2. **防抖处理**：歌曲稳定播放 3 秒后触发乐评生成
3. **缓存检查**：先查询 SQLite 缓存，命中则直接返回
4. **AI 生成**：调用 AI Provider 生成乐评，解析 JSON 响应
5. **缓存存储**：将乐评存入 SQLite 缓存
6. **前端展示**：Web 界面轮询 API 获取最新乐评

### 关键设计模式
- **Provider 模式**：AI 调用抽象为 `BaseProvider`，支持多种 AI 提供商
- **工厂模式**：`create_app()` 创建 FastAPI 应用实例
- **回调模式**：媒体变化时通过回调函数处理业务逻辑
- **缓存策略**：同一首歌只请求一次 AI，后续读取缓存

### 错误处理
- AI 请求超时：记录日志，返回空结果
- API 错误：根据状态码提供友好错误信息
- 配置缺失：使用默认值，记录警告日志

## 注意事项

1. **平台限制**：仅支持 Windows 系统，依赖 `winsdk` 库
2. **API Key 安全**：配置文件包含敏感信息，切勿上传至 Git
3. **网络依赖**：AI 功能需要网络连接，离线时只能使用缓存
4. **端口占用**：默认端口 5800，确保未被其他服务占用

## 常见问题

### Q: 如何更换 AI 提供商？
A: 编辑 `~/.mylody/config.yaml`，修改 `ai.provider` 和 `ai.model`，重启服务。

### Q: 如何清除缓存？
A: 删除 `~/.mylody/cache/` 目录下的 SQLite 数据库文件。

### Q: 如何查看日志？
A: 日志文件位于 `~/.mylody/logs/` 目录，可通过 `logging.level` 配置日志级别。

### Q: 支持哪些音乐播放器？
A: 支持所有使用 Windows SMTC API 的播放器，包括 Spotify、网易云音乐、Apple Music、Windows Media Player 等。

## 相关链接

- **项目灵感**：[Melory iOS 应用](https://apps.apple.com/cn/app/id6756657818)
- **FastAPI 文档**：https://fastapi.tiangolo.com/
- **Anthropic API**：https://docs.anthropic.com/
- **OpenAI API**：https://platform.openai.com/docs