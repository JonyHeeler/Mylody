# Mylody — 产品需求文档 (PRD)

> **版本**：v0.1.0-draft  
> **状态**：草稿，供 AI 协作构建使用  
> **最后更新**：2026-05

---

## 1. 产品概述

**Mylody** 是一款运行在 Windows 桌面端的轻量工具，能够自动识别当前正在播放的音乐，调用 AI 接口生成一份结构化乐评报告，并将报告缓存在本地——下次再播放同一首歌时，直接读取缓存，无需重复请求 AI。

### 1.1 目标用户

- 热爱音乐、希望深入了解正在听的曲目的普通用户
- 希望快速获得专业视角乐评的学生或音乐爱好者

### 1.2 核心价值

| 价值点 | 说明 |
|---|---|
| 零打扰 | 在后台静默监听，不干扰用户正常收听 |
| 即时洞察 | 播放时自动触发，几秒内获得乐评 |
| 节省算力 | 本地缓存机制，同一首歌只请求一次 AI |
| 隐私优先 | API Key 与所有配置均保存在本地，不上传 |

---

## 2. 功能模块

### 2.1 模块总览

```
Mylody
├── 音乐监听模块      # 读取 Windows 当前播放信息
├── AI 请求模块       # 构造 Prompt，调用 AI 接口
├── 缓存管理模块      # 本地存储与检索乐评报告
├── 配置管理模块      # 读取 .env / config 文件
└── UI 展示模块       # 在系统托盘 / 悬浮窗展示乐评
```

---

### 2.2 音乐监听模块

**目标**：获取 Windows 系统当前播放的歌曲名、艺术家、专辑等元数据。

**实现方案**：

- 主方案：调用 **Windows Runtime API (WinRT)**，通过 `Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager` 获取当前媒体会话信息，兼容 Spotify、网易云音乐、Windows Media Player、YouTube（浏览器）等。
- 备用方案：若 WinRT 返回为空（部分老旧播放器不支持），可尝试解析进程窗口标题（Window Title Parsing）。

**返回数据结构**：

```json
{
  "title": "Counting Stars",
  "artist": "OneRepublic",
  "album": "Native",
  "duration_seconds": 257,
  "source_app": "Spotify",
  "fetched_at": "2026-05-28T14:32:00Z"
}
```

**边界处理**：

| 场景 | 处理方式 |
|---|---|
| 无媒体会话 / 无歌曲播放 | 静默等待，不触发 AI 请求；UI 显示"暂无播放" |
| 仅有视频（非音乐）播放 | 通过黑名单（如 `vlc.exe` 播放视频文件扩展名）过滤，可配置 |
| 歌曲信息残缺（只有标题无艺术家） | 仍可请求 AI，Prompt 中标注信息不完整 |
| 同一首歌反复切换 | 防抖处理：歌曲稳定播放 **3 秒**后再触发，避免刷屏 |
| WinRT API 调用失败 | 捕获异常，日志记录，切换备用方案；若仍失败则提示用户 |

---

### 2.3 AI 请求模块

**目标**：根据歌曲元数据，向 AI 接口发送请求并获取结构化乐评。

**支持的 AI 提供商**（通过配置切换）：

- Anthropic Claude（默认）
- OpenAI GPT 系列
- 其他兼容 OpenAI 格式的接口（如 DeepSeek、通义千问等）

#### 2.3.1 Prompt 设计

**系统 Prompt（System Prompt）**：

```
你是一位专业的乐评人，擅长从音乐理论、情感表达、文化背景和创作背景多个维度分析歌曲。
你的乐评风格简洁有深度，面向普通音乐爱好者，避免过度专业术语堆砌。
请严格按照 JSON 格式返回，不要输出任何 JSON 以外的内容。
```

**用户 Prompt（User Prompt）**：

```
请为以下歌曲生成一份乐评报告：

歌曲名称：{{title}}
艺术家：{{artist}}
专辑：{{album}}（如未知请忽略此字段）
播放来源：{{source_app}}

请按照以下 JSON 结构返回：
{
  "summary": "一句话概括这首歌的风格与氛围（30字以内）",
  "emotion": "情感基调，如：励志、忧郁、浪漫、躁动等",
  "background": "创作背景或艺术家简介（100字以内）",
  "musicology": "音乐理论视角的简析，如调性、节奏、编曲特点（100字以内）",
  "why_listen": "推荐理由：这首歌适合在什么场景下收听（50字以内）",
  "similar_songs": ["相似歌曲1 - 艺术家", "相似歌曲2 - 艺术家"],
  "rating": 8.5
}
```

**边界处理**：

| 场景 | 处理方式 |
|---|---|
| AI 返回非 JSON 格式 | 捕获解析异常，记录原始返回，UI 显示"解析失败，请重试" |
| AI 接口超时（>15s） | 中止请求，显示超时提示，不写入缓存 |
| 歌曲 AI 不认识（冷门曲目） | AI 会在 `background` 字段注明"未找到相关资料"，乐评仍保存 |
| API Key 未配置 | 启动时检测，提示用户前往配置文件填写 Key |
| API 返回错误码（401/429/500） | 对应提示：Key 无效 / 超出速率限制 / 服务暂不可用 |
| 网络不可用 | 检测到无网络时，跳过 AI 请求，如有缓存则直接展示缓存 |

---

### 2.4 缓存管理模块

**目标**：将每首歌的乐评报告持久化到本地，下次播放时直接读取。

**缓存 Key 规则**：

```
{artist}::{title}
```

示例：`OneRepublic::Counting Stars`

- Key 经过 **小写化 + 去首尾空格** 标准化处理，避免大小写不一致导致缓存未命中。
- 若 `artist` 为空，Key 降级为 `UNKNOWN::{title}`。

**存储格式**：

```
~/.mylody/cache/
└── reviews.db          # SQLite 数据库（主要存储）
```

**数据表结构（SQLite）**：

```sql
CREATE TABLE reviews (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cache_key   TEXT UNIQUE NOT NULL,   -- "{artist}::{title}" 标准化后
  title       TEXT NOT NULL,
  artist      TEXT,
  album       TEXT,
  review_json TEXT NOT NULL,          -- AI 返回的完整 JSON 字符串
  ai_model    TEXT,                   -- 生成该乐评使用的模型名
  created_at  TEXT NOT NULL,          -- ISO 8601
  updated_at  TEXT NOT NULL
);
```

**缓存命中流程**：

```
播放歌曲
  └─> 生成 cache_key
        ├─> 命中缓存 ──────> 直接读取 review_json，展示乐评
        └─> 未命中    ──────> 调用 AI 接口 ──> 写入缓存 ──> 展示乐评
```

**边界处理**：

| 场景 | 处理方式 |
|---|---|
| 数据库文件损坏 | 捕获异常，自动备份损坏文件，重建空数据库，记录日志 |
| 磁盘空间不足 | 写入前检测可用空间，若 < 10MB 则警告用户并跳过写入 |
| 用户手动删除缓存目录 | 下次启动时自动重建目录结构 |
| 强制刷新乐评 | 支持右键菜单"刷新乐评"，重新请求 AI 并覆盖缓存 |
| 缓存数据过期 | 默认不过期；用户可在配置中设置 `cache_ttl_days`（0 = 永不过期） |

---

### 2.5 配置管理模块

**目标**：让用户在本地安全管理 API Key 及各项参数，不上传任何敏感信息。

#### 2.5.1 配置文件结构

```
~/.mylody/
├── config.yaml          # 用户实际配置（不加入版本控制）
├── config.example.yaml  # 示例配置（随程序分发，只读）
├── cache/
│   └── reviews.db
└── logs/
    └── mylody.log
```

#### 2.5.2 示例配置文件（`config.example.yaml`）

```yaml
# =============================================
#  Mylody 配置文件示例
#  1. 将此文件复制为 config.yaml
#  2. 按注释填写你的配置
#  3. 切勿将 config.yaml 上传至 Git 或分享给他人
# =============================================

# --- AI 接口配置 ---
ai:
  provider: "anthropic"          # 可选: anthropic | openai | custom
  api_key: "YOUR_API_KEY_HERE"   # ← 填写你的 API Key
  model: "claude-sonnet-4-20250514"  # 使用的模型名称
  base_url: ""                   # 仅 custom provider 需要填写，如 https://api.deepseek.com
  timeout_seconds: 15            # 请求超时时间
  max_retries: 2                 # 失败自动重试次数

# --- 缓存配置 ---
cache:
  enabled: true
  cache_ttl_days: 0              # 0 = 永不过期；设置正整数则按天过期
  db_path: ""                    # 留空则使用默认路径 ~/.mylody/cache/reviews.db

# --- 音乐监听配置 ---
listener:
  poll_interval_seconds: 2       # 检测当前播放歌曲的频率
  debounce_seconds: 3            # 歌曲稳定播放多少秒后触发乐评
  excluded_apps: []              # 排除的应用进程名，如 ["vlc.exe", "powerdvd.exe"]

# --- 展示配置 ---
display:
  show_in_tray: true             # 是否在系统托盘显示图标
  auto_show_review: true         # 检测到新歌时是否自动弹出乐评
  language: "zh-CN"              # 乐评语言: zh-CN | en-US | ja-JP

# --- 日志配置 ---
logging:
  level: "INFO"                  # DEBUG | INFO | WARNING | ERROR
  max_file_size_mb: 5
  backup_count: 3
```

**边界处理**：

| 场景 | 处理方式 |
|---|---|
| `config.yaml` 不存在 | 启动时自动从 `config.example.yaml` 复制，提示用户填写 API Key |
| API Key 为默认占位符 `YOUR_API_KEY_HERE` | 检测并提示"请填写有效的 API Key"，程序可运行但禁用 AI 功能 |
| 配置字段缺失 | 使用内置默认值，不崩溃 |
| 配置文件格式错误（YAML 语法错误） | 捕获解析异常，提示具体出错行号，退出并打印帮助信息 |
| 用户设置了无效的 `provider` 值 | 提示可选值列表，回退到 `anthropic` |

---

### 2.6 UI 展示模块

**展示形式**（MVP 阶段优先实现托盘+通知）：

- **系统托盘图标**：Mylody 常驻托盘，右键可查看当前乐评 / 刷新 / 打开设置 / 退出
- **悬浮通知卡片**：新歌播放后自动弹出，3-5 秒后收起（可配置）
- **主窗口**：点击托盘图标展开，展示完整乐评报告（含相似推荐、评分等）

---

## 3. 产品构建路线图

### Phase 0 — 项目初始化（预计 1-2 天）

- [ ] 初始化项目仓库，选定技术栈（推荐：Python 3.11+ 或 Node.js + Electron）
- [ ] 创建目录结构与 `config.example.yaml`
- [ ] 实现配置加载模块（读取 YAML，验证字段，处理缺失/异常）
- [ ] 搭建日志系统（写入文件 + 控制台双输出）
- [ ] 编写 README，说明如何从 `config.example.yaml` 复制并填写 Key

**验收标准**：程序启动后，能正确加载配置，若 Key 未填写则打印提示并正常运行。

---

### Phase 1 — 音乐监听（预计 2-3 天）

- [ ] 集成 WinRT 媒体会话 API（Python：`winsdk` 库；Node.js：`node-winrt`）
- [ ] 实现防抖逻辑（稳定播放 N 秒后才触发）
- [ ] 实现进程名过滤黑名单
- [ ] 单元测试：模拟无媒体会话、信息残缺、快速切歌等场景
- [ ] 控制台输出当前播放歌曲信息（用于调试）

**验收标准**：播放 Spotify / 网易云音乐时，控制台能正确打印歌曲名和艺术家。

---

### Phase 2 — AI 请求与乐评生成（预计 2-3 天）

- [ ] 实现 AI 请求模块，支持 Anthropic / OpenAI 两种 provider
- [ ] 实现 Prompt 模板（支持变量替换）
- [ ] 实现 JSON 响应解析与验证
- [ ] 处理超时、网络错误、API 错误码
- [ ] 命令行测试：给定歌曲名，输出乐评 JSON

**验收标准**：给定 `{"title": "Counting Stars", "artist": "OneRepublic"}`，能返回符合结构的乐评 JSON。

---

### Phase 3 — 本地缓存（预计 1-2 天）

- [ ] 集成 SQLite，创建 `reviews` 表
- [ ] 实现缓存读写（命中/未命中逻辑）
- [ ] 实现 cache_key 标准化（小写 + trim）
- [ ] 实现强制刷新接口
- [ ] 数据库异常恢复（损坏时自动重建）

**验收标准**：第一次播放后写入缓存；第二次播放同一首歌，不产生 AI 请求，直接从数据库读取。

---

### Phase 4 — 系统托盘 UI（预计 3-5 天）

- [ ] 系统托盘图标与右键菜单（查看乐评 / 刷新 / 设置 / 退出）
- [ ] 悬浮通知卡片（自动弹出 + 自动收起）
- [ ] 主窗口展示完整乐评（评分、背景、推荐）
- [ ] 设置页面（直接编辑常用配置项，无需手动改 YAML）

**验收标准**：能在托盘看到图标，播放新歌时自动弹出通知卡片展示乐评。

---

### Phase 5 — 打包与分发（预计 1-2 天）

- [ ] 打包为单个 `.exe`（Python：PyInstaller；Node.js：electron-builder）
- [ ] 开机自启动选项
- [ ] 安装向导，首次运行引导用户填写 API Key
- [ ] 编写用户文档（安装 + 使用 + FAQ）

---

### 未来规划（Backlog）

- 支持更多 AI 提供商（Gemini、本地 Ollama 等）
- 乐评历史浏览与搜索（"我最近听过的乐评"）
- 导出乐评为 PDF / Markdown
- 多语言乐评支持
- macOS / Linux 版本

---

## 4. 技术选型建议

| 模块 | Python 方案 | Electron 方案 |
|---|---|---|
| 音乐监听 | `winsdk` / `pywin32` | `node-winrt` / FFI |
| AI 请求 | `anthropic` / `openai` SDK | `@anthropic-ai/sdk` |
| 缓存 | `sqlite3` / `sqlalchemy` | `better-sqlite3` |
| 配置读取 | `pyyaml` | `js-yaml` |
| UI | `pystray` + `tkinter` / `PyQt` | Electron（HTML/CSS/JS） |
| 打包 | PyInstaller | electron-builder |

> **推荐**：若 UI 需求简单（托盘 + 通知），优先选 **Python + pystray**，开发更快。若未来需要精美 UI，选 **Electron**。

---

## 5. 目录结构参考

```
mylody/
├── config.example.yaml      # 示例配置（随包分发）
├── README.md
├── requirements.txt         # 或 package.json
├── main.py                  # 入口文件
├── mylody/
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── listener.py          # 音乐监听
│   ├── ai_client.py         # AI 请求
│   ├── cache.py             # 缓存管理
│   ├── prompt.py            # Prompt 模板
│   └── ui/
│       ├── tray.py          # 系统托盘
│       ├── notification.py  # 通知卡片
│       └── window.py        # 主窗口
└── tests/
    ├── test_listener.py
    ├── test_ai_client.py
    └── test_cache.py
```

---

## 6. 安全与隐私原则

1. **API Key 只存本地**：`config.yaml` 绝不上传；`.gitignore` 中默认排除。
2. **无遥测**：程序不收集任何使用数据，不与第三方服务通信（除 AI 接口外）。
3. **AI 请求最小化**：只发送歌曲元数据（名称、艺术家、专辑），不发送用户信息。
4. **缓存只存本地**：`reviews.db` 保存在用户主目录，用户可随时删除。

---

## 7. 给 AI 协作者的说明

> 本文档是 Mylody 项目的完整需求规格。在与 AI 协作构建时，请遵循以下原则：

1. **先读文档再写代码**：每次新建模块前，确认对应章节的需求和边界处理已理解。
2. **配置优先**：第一步永远是复制 `config.example.yaml` 为 `config.yaml`，填写 API Key。
3. **按 Phase 推进**：不要跳过阶段，每个 Phase 有明确验收标准，验收后再进入下一阶段。
4. **边界先行**：实现每个功能时，对应的边界处理（错误、异常、空值）同步实现，不留技术债。
5. **不要硬编码**：API Key、路径、模型名等均从配置读取，禁止写死在代码中。
