# Mylody AI Agent

音乐乐评 AI Agent — 自动识别当前播放的音乐，调用 AI 生成专业乐评。

本项目灵感来源为 iOS 应用 Melory，下载地址：https://apps.apple.com/cn/app/id6756657818。

本项目为 2025-2026-2 学期《AI 智能体产品设计》课程第 13 周作业。

如有建议。欢迎给我发邮件。我的联系方式在主页。

## 功能

- **自动监听**：通过 Windows SMTC API 读取当前播放的歌曲信息（支持 Spotify、网易云、Apple Music 等）
- **AI 乐评**：调用 Claude / OpenAI 生成专业中文乐评，包含情感分析、乐理解析、创作背景等
- **本地缓存**：SQLite 存储，同一首歌只请求一次 AI，后续直接读取缓存
- **Web 界面**：浏览器打开 `http://localhost:5800` 查看乐评

## 环境要求

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Windows | 10/11 | 需要 Windows Media Control API 支持 |
| Python | 3.11+ | 推荐 3.11，兼容 3.12/3.13 |
| 网络 | 需要 | 调用 AI API 需要网络连接 |

> **注意**：本项目依赖 `winsdk` 库，仅支持 Windows 系统。

## 快速开始

### 1. 创建虚拟环境

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

首次运行会自动生成 `~/.mylody/config.yaml`，编辑填写你的 API Key：

```yaml
ai:
  provider: "anthropic"    # 可选: anthropic | openai | custom
  api_key: "sk-ant-xxxxx"  # ← 填写你的 API Key
  model: "claude-sonnet-4-20250514"
```

### 4. 启动

```bash
python main.py
```

浏览器打开 http://localhost:5800

## 命令行参数

```bash
python main.py --port 8080          # 指定端口
python main.py --config ./my.yaml   # 指定配置文件
```

## 支持的 AI 提供商

| 提供商 | 配置值 | 说明 |
|---|---|---|
| Anthropic | `anthropic` | 默认，Claude 系列 |
| OpenAI | `openai` | GPT 系列 |
| 自定义 | `custom` | 兼容 OpenAI 格式的接口（如 DeepSeek、通义千问） |

## 项目结构

```
mylody/              # 后端（Python + FastAPI）
├── ai/              AI 请求模块（Prompt + Provider）
├── cache/           SQLite 缓存管理
├── listener/        Windows 媒体会话监听
├── server/          FastAPI 路由
└── utils/           工具函数

web/                 # 前端（HTML + CSS + JS）
├── index.html
├── style.css
└── app.js
```

## 配置说明

配置文件位于 `~/.mylody/config.yaml`，主要配置项：

```yaml
ai:
  provider: "anthropic"
  api_key: "YOUR_API_KEY"
  model: "claude-sonnet-4-20250514"
  timeout_seconds: 15

listener:
  poll_interval_seconds: 2   # 检测频率
  debounce_seconds: 3        # 防抖时间
  excluded_apps: []          # 排除的应用

cache:
  enabled: true
  cache_ttl_days: 0          # 0 = 永不过期

server:
  host: "127.0.0.1"
  port: 5800
```