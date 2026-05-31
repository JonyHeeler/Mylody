# AI Pitchfork: Windows Now Playing 乐评 Agent 调研结论

日期：2026-05-28

## 目标

做一个 Windows 本地 agent，用来监听当前正在播放的音乐，读取歌曲名称、歌手、专辑等信息，然后发送给 AI 生成乐评。对于已经生成过的乐评，以固定格式存储在本地；下次播放同一首歌时，直接读取本地缓存，不重复请求 AI。

## 核心结论

这个方案可行，而且是一个很稳的 MVP 路线。

原因是它不需要读取 Apple Music App 的内部资料库，也不需要读取或上传音频文件，只需要读取 Windows 系统级的 Now Playing / SMTC 媒体会话。Apple Music for Windows 通常会把当前播放信息暴露给 Windows 系统媒体控件，因此可以通过 Windows 本地接口拿到歌名、歌手、专辑等元数据。

需要注意的是：这个方案读取的是“当前播放信息”，不是 Apple Music 的完整资料库，也不是音频文件本身。

## 可以读取到的信息

通过 Windows `GlobalSystemMediaTransportControlsSessionManager` 通常可以读取：

- 歌名：`title`
- 歌手：`artist`
- 专辑：`albumTitle`
- 专辑艺人：`albumArtist`
- 播放状态：播放中、暂停、停止
- 播放进度：取决于 App 是否暴露
- 歌曲时长：取决于 App 是否暴露
- 来源应用：`sourceAppUserModelId`

其中对当前需求最关键的是：

- `title`
- `artist`
- `albumTitle`
- `sourceAppUserModelId`

## 不建议走的路线

### 不建议读取 Apple Music 内部资料库

新版 Apple Music for Windows 没有稳定、公开、适合第三方使用的本地资料库 API。Apple 官方文档主要提供的是用户手动导入、查看文件位置、改变媒体文件夹等操作，并没有给第三方程序提供完整读取 Apple Music 本地库的接口。

### 不建议一开始读取音频文件

当前目标是生成乐评，不是做音频分析。只用歌曲元数据已经可以做出不错的 MVP。读取音频会引入版权、DRM、文件匹配、转码、性能等额外复杂度。

### 不建议依赖旧 iTunes COM 作为主路线

旧版 iTunes for Windows 有 COM 自动化接口，可以读取资料库、播放列表和当前曲目信息。但新版 Apple Music for Windows 不等同于旧 iTunes。iTunes COM 可以作为兼容模式，而不是主路线。

## 推荐架构

```text
Windows Now Playing 监听
        |
        v
读取 title / artist / album / source app
        |
        v
生成 normalized_key
        |
        v
查询本地 SQLite 缓存
        |
        +-- 命中：直接返回已有乐评
        |
        +-- 未命中：调用 AI 生成乐评
                       |
                       v
                  写入本地 SQLite
```

## 技术选型

### 首选方案

```text
.NET 8
Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager
SQLite
OpenAI API
WPF / WinUI 3 / 托盘程序
```

这个组合最适合 Windows 本地 agent：

- `.NET` 调 Windows 原生接口更顺手
- `GlobalSystemMediaTransportControlsSessionManager` 是读取系统媒体会话的关键接口
- `SQLite` 适合本地缓存和查询
- `WPF` 或 `WinUI 3` 可以做桌面 UI
- 也可以先做无 UI 的 console / worker service MVP

### 备选方案

```text
Electron / Tauri
.NET sidecar 负责读取 Windows Now Playing
SQLite
OpenAI API
```

如果后续想做跨平台或更精致的 UI，可以考虑 Electron 或 Tauri。但读取 Windows Now Playing 这部分，仍建议交给 `.NET` sidecar。

## 本地缓存设计

建议使用 SQLite，而不是一开始用零散的 Markdown 或 JSON 文件。

原因：

- 方便按歌名、歌手、专辑查询
- 方便记录播放次数
- 方便记录 AI 模型和 prompt 版本
- 方便以后做搜索、筛选、重新生成、导出

### 表结构建议

```sql
CREATE TABLE tracks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  artist TEXT,
  album TEXT,
  album_artist TEXT,
  source_app_id TEXT,
  normalized_key TEXT NOT NULL UNIQUE,
  first_seen_at TEXT NOT NULL,
  last_played_at TEXT NOT NULL,
  play_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  track_id INTEGER NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  review_text TEXT NOT NULL,
  summary TEXT,
  tags_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(track_id) REFERENCES tracks(id)
);
```

## 缓存 key 设计

MVP 阶段可以使用：

```text
lower(trim(title)) + "::" + lower(trim(artist)) + "::" + lower(trim(album))
```

例如：

```text
let down::radiohead::ok computer
```

后续可以增强：

- 去掉多余空格
- 统一全角和半角字符
- 处理大小写
- 处理 `feat.`
- 处理 `remastered`
- 处理 `explicit`
- 处理 live / demo / deluxe edition 等版本差异

## Agent 工作流

1. 启动程序。
2. 请求 Windows Now Playing 会话。
3. 监听当前活跃媒体会话变化。
4. 过滤来源应用，例如只处理 Apple Music，或允许用户选择播放器。
5. 读取当前曲目的 `title / artist / album`。
6. 等待 3 到 5 秒 debounce，避免用户快速切歌时重复请求。
7. 生成 `normalized_key`。
8. 查询 SQLite。
9. 如果已有乐评，直接展示或返回。
10. 如果没有乐评，调用 AI 生成。
11. 把 AI 乐评、摘要、标签、模型、prompt 版本写入 SQLite。

## AI 输入建议

MVP 阶段可以发送：

```json
{
  "title": "歌曲名",
  "artist": "歌手",
  "album": "专辑名",
  "language": "zh-CN",
  "style": "像专业音乐媒体一样，兼顾普通听众可读性"
}
```

可以让 AI 输出固定 JSON，便于存储：

```json
{
  "summary": "一句话短评",
  "review": "完整乐评",
  "tags": ["art pop", "melancholic", "cinematic"],
  "score": 8.4
}
```

## 需要注意的坑

- Apple Music 是否暴露完整 metadata 取决于它当前版本和播放内容，但歌名、歌手、专辑通常够用。
- Windows 系统里可能同时存在多个媒体会话，例如浏览器、Spotify、Apple Music，需要通过 `sourceAppUserModelId` 做过滤或让用户选择。
- 用户快速切歌时，要做 debounce，避免浪费 token。
- 同一首歌可能因为专辑版本不同产生不同 key，MVP 可以接受，后续再做模糊匹配。
- AI 乐评应保存 `prompt_version`，以后升级提示词时可以选择重新生成。
- 如果没有读取到专辑名，仍然可以用歌名和歌手生成乐评，但缓存命中准确度会下降。

## MVP 范围

第一版只做这些：

- 监听当前播放曲目
- 读取歌名、歌手、专辑
- 根据三者生成缓存 key
- 查 SQLite
- 未命中时调用 AI 生成中文乐评
- 保存乐评到 SQLite
- 下次播放同一首歌时直接返回本地乐评

暂时不做：

- 读取 Apple Music 完整资料库
- 读取音频文件
- 分析音频波形
- 歌词识别
- DRM 内容处理
- 多平台兼容

## 参考资料

- Microsoft SMTC 文档：https://learn.microsoft.com/en-us/windows/apps/develop/media-playback/integrate-with-systemmediatransportcontrols
- Microsoft `GlobalSystemMediaTransportControlsSessionManager.RequestAsync` 文档：https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmanager.requestasync
- Apple Music Windows 导入本地音乐：https://support.apple.com/en-sg/guide/music-windows/mus3081/1.6/windows/10
- Apple Music Windows 文件位置说明：https://support.apple.com/en-sg/guide/music-windows/mus69248042d/windows

## 最终判断

这个项目可以从一个很小但完整的 MVP 开始：

```text
Now Playing metadata -> AI review -> SQLite cache -> repeat playback cache hit
```

这条路线避开了 Apple Music 私有资料库、音频文件读取和 DRM 问题，技术风险低，用户体验也自然。对于个人工具或本地 agent 来说，这是最合适的第一步。
