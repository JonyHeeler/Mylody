# Mylody

Windows 桌面音乐乐评工具 — 自动识别当前播放的音乐，调用 AI 生成结构化乐评。

## 功能

- **自动监听**：通过 Windows SMTC API 读取当前播放的歌曲信息
- **AI 乐评**：调用 Claude / OpenAI 生成专业乐评
- **本地缓存**：SQLite 存储，同一首歌不重复请求
- **Web 界面**：浏览器打开 `http://localhost:5800` 查看乐评

## 项目结构

```
mylody/          # 后端（Python + FastAPI）
├── config.py        配置管理
├── listener/        Windows 媒体会话监听
├── server/          FastAPI 路由
├── ai_client.py     AI 请求
├── cache.py         缓存管理
└── utils/           工具函数

web/             # 前端（HTML + CSS + JS）
├── index.html
├── style.css
└── app.js
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

首次运行会自动生成 `~/.mylody/config.yaml`，编辑填写你的 API Key：

```yaml
ai:
  provider: "anthropic"
  api_key: "sk-ant-xxxxx"
```

### 3. 启动

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
| 自定义 | `custom` | 兼容 OpenAI 格式的接口 |

## 开发规范

- 单文件 ≤ 200 行
- 模块化，极限解耦
- 所有导出函数必须有 docstring
- 前后端完全分离

## License

MIT
