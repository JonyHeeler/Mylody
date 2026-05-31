# Mylody 反幻觉能力建设详细计划

日期：2026-05-30

目标：在不牺牲乐评可读性的前提下，降低 Mylody 在发行背景、制作人、编曲、乐理、奖项、采样、创作故事等具体事实上的幻觉风险。

---

## 1. 当前判断

Mylody 当前链路是：

```text
Windows SMTC 当前播放信息
  -> title / artist / album
  -> AI 直接生成乐评 JSON
  -> SQLite 缓存
  -> Web 展示
```

主要风险不在于模型“不会写”，而在于输入证据不足：

- 当前输入通常只有 `title / artist / album`。
- 现有 prompt 却要求模型写发行背景、专辑位置、制作人、编曲、人声、鼓点、贝斯、合成器、Hook、Bridge、调性、节奏推进等内容。
- `AIClient` 目前只做 JSON 解析，不校验事实边界。
- 缓存没有 schema/version 隔离，旧 prompt 生成的幻觉乐评会继续命中。

因此，本阶段不应该优先追求“让模型自由联网知道更多”，而应该先建立：

```text
证据边界 -> 事实分级 -> 写作隔离 -> 输出校验 -> 缓存隔离
```

---

## 2. 总体架构建议

推荐把“搜索资料”和“撰写乐评”拆成两个 AI/工具角色。

```text
MediaInfo
  title / artist / album / source_app
        |
        v
Track Resolver
  规范化曲目、消歧、生成 canonical track identity
        |
        v
Evidence Providers
  MusicBrainz / Last.fm / Discogs / 搜索 API / 手动资料
        |
        v
Evidence Bundle
  known_facts / uncertain_facts / source_urls / confidence
        |
        v
Review Writer
  只基于 Evidence Bundle 和元数据写乐评
        |
        v
Review Guardrails
  schema 校验、事实风险词校验、必要时 retry repair
        |
        v
SQLite Cache
  按 schema_version / evidence_version 隔离
        |
        v
Web UI
  展示乐评、可信度、资料来源、不确定事实
```

关键原则：

1. **搜索模块可以联网，写作模块默认不联网。**
2. **写作模型不能把自己记忆里的内容当作事实。**
3. **所有具体事实必须来自 `EvidenceBundle.known_facts`。**
4. **不确定内容只能进入 `uncertain_facts`，不能混进正文。**
5. **没有证据时，允许写听感、情绪、风格、场景，但不能写具体发行史。**

---

## 3. 数据结构设计

### 3.1 ReviewData v2

建议扩展 `mylody/types.py`：

```python
@dataclass
class ReviewData:
    summary: str = ""
    emotion: str = ""
    background: str = ""
    musicology: str = ""
    why_listen: str = ""
    similar_songs: list[str] = field(default_factory=list)
    rating: float = 0.0

    factuality_level: str = "metadata_only"
    analysis_basis: str = "track_metadata"
    known_facts: list[str] = field(default_factory=list)
    uncertain_facts: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    evidence_sources: list[dict] = field(default_factory=list)
    schema_version: str = "review_v2"
```

字段含义：

| 字段 | 说明 |
|---|---|
| `factuality_level` | `metadata_only` / `grounded` / `mixed` |
| `analysis_basis` | `track_metadata` / `provided_context` / `external_evidence` |
| `known_facts` | 证据明确支持的事实 |
| `uncertain_facts` | 有可能相关但证据不足的信息 |
| `safety_notes` | 被降级、删除、限制的风险点 |
| `evidence_sources` | 来源 URL、平台、字段、置信度 |
| `schema_version` | 用于缓存隔离 |

### 3.2 EvidenceBundle

新增 `mylody/evidence/types.py`：

```python
@dataclass
class EvidenceSource:
    provider: str
    url: str = ""
    title: str = ""
    retrieved_at: str = ""


@dataclass
class EvidenceFact:
    key: str
    value: str
    source: str
    confidence: float = 0.0


@dataclass
class EvidenceBundle:
    track_title: str
    artist: str
    album: str = ""
    canonical_id: str = ""
    known_facts: list[EvidenceFact] = field(default_factory=list)
    uncertain_facts: list[EvidenceFact] = field(default_factory=list)
    sources: list[EvidenceSource] = field(default_factory=list)
    confidence: float = 0.0
    evidence_version: str = "evidence_v1"
```

Evidence 层的输出要尽量结构化，不要直接丢一大段网页文本给乐评模型。

---

## 4. 音乐元数据 API 接入建议

### 4.1 第一优先级：MusicBrainz

适合作为主数据源：

- 开放、免费、音乐元数据导向。
- 可查 recording、release、artist、release-group。
- 有 MBID，适合做 canonical track identity。
- 适合解决“这首歌到底是哪一首”的问题。

建议第一版只做：

```text
title + artist + album
  -> MusicBrainz recording search
  -> 取 top 3 candidates
  -> 根据 artist / album / title 相似度打分
  -> 高置信度才进入 known_facts
```

不要一开始就做复杂 credits、alias、版本合并。

### 4.2 第二优先级：Last.fm

适合补充：

- tags
- listeners / playcount
- similar tracks
- 简短 wiki / artist bio

注意：

- Last.fm 的 wiki/简介适合做参考，不适合无条件进入事实正文。
- tags 可以用于风格描述，但不要把 tags 当作严格音乐学事实。

### 4.3 第三优先级：Discogs

适合补充：

- release
- label
- credits
- formats
- 版本信息

注意：

- 版本信息复杂，容易误匹配。
- 接入成本高于 MusicBrainz。
- 建议等 Track Resolver 稳定后再接。

### 4.4 Spotify / Apple Music

适合：

- 曲目匹配
- ISRC
- 封面图
- album / artist 基本信息

不建议：

- 把平台内容直接喂给模型作为事实长文本。
- 依赖平台内容生成背景故事。

---

## 5. AI 搜索能力选择

### 5.1 不推荐把联网搜索直接交给乐评模型

原因：

- 模型可能选择性引用网页，难以稳定复现。
- 搜索结果质量波动大。
- 乐评模型会把搜索片段和自身记忆混在一起。
- 缓存难以判断是哪一版证据生成的。

更稳的方式：

```text
Search Agent / Evidence Provider
  -> 只返回结构化证据

Review Writer
  -> 只基于结构化证据写作
```

### 5.2 国内常见模型/平台联网搜索支持情况

说明：这里的“支持”分三类：

- **A 类：API 原生可控搜索**，可通过参数或 tool 在 API 调用中开启。
- **B 类：平台/应用端支持搜索**，但不一定能在通用 API 里稳定控制。
- **C 类：不建议依赖原生搜索**，建议自己接搜索 API 或元数据 API。

| 平台/模型 | API 联网搜索判断 | 适合 Mylody 的用法 |
|---|---|---|
| 通义千问 / Qwen / DashScope | A 类。常见用法是 `enable_search` 或搜索增强相关参数。 | 可作为 Search Agent，但仍建议把结果整理成 EvidenceBundle 后再给 writer。 |
| 智谱 GLM | A 类。常见能力包括 `web_search` 工具/搜索参数。 | 适合做搜索型 evidence agent。注意保留 search result URL。 |
| Kimi / Moonshot | A/B 类。Kimi 产品端搜索强，API 侧能力需要按具体接口确认。 | 如果 API 能返回引用来源，可用于补背景；否则不作为主证据源。 |
| 豆包 / 火山方舟 | A/B 类。方舟生态有联网/搜索增强能力，但具体模型和接口支持要区分。 | 可作为备选 search provider，不建议直接替代 MusicBrainz。 |
| MiniMax / Mimo | A/B 类。你提到 Mimo 可以联网搜索，适合做搜索 agent 候选。 | 若 API 能返回来源和摘要，可接入 Evidence Provider。 |
| 百度文心 / 千帆 | B 类。产品和平台有搜索增强/RAG能力，但通用 Chat API 能否原生联网要按模型与服务确认。 | 更适合走自建搜索/RAG，不优先作为原生搜索依赖。 |
| 腾讯混元 | B/C 类。需要区分模型对话 API、知识引擎、搜索增强产品。 | 不作为第一批接入。 |
| 讯飞星火 | B/C 类。产品侧联网能力和 API 能力需区分。 | 不作为第一批接入。 |
| 360 智脑 / 纳米 AI | B 类。产品搜索能力强，但 API 接入形态不一定适合本项目。 | 更适合人工调研，不作为核心链路。 |
| DeepSeek | C 类。标准 API 更明确的是 JSON Output 和 Tool Calls；搜索应由应用自己提供工具。 | 用 DeepSeek 写乐评可以，但搜索建议由 Mylody 自己实现。 |

结论：

1. 如果要快速验证“模型原生搜索”，优先看通义千问、智谱 GLM、Mimo。
2. 如果要做可控、可复现、可测试的反幻觉，优先做 MusicBrainz + EvidenceBundle。
3. DeepSeek 更适合作为 writer model，不适合作为唯一搜索方案。

---

## 6. 模块拆分计划

### 6.1 AI 写作模块

现有文件：

```text
mylody/ai/prompt.py
mylody/ai/client.py
mylody/ai/provider_base.py
mylody/ai/provider_openai.py
mylody/ai/provider_anthropic.py
```

改造目标：

1. `SYSTEM_PROMPT` 改成 Safe Review Prompt。
2. `build_user_prompt(track, evidence=None)` 支持传入证据。
3. Provider 增加可选 JSON/schema 输出参数。
4. `AIClient.generate_review()` 生成后进入 guardrails 校验。
5. 校验失败时最多 retry repair 一次。

### 6.2 Evidence 模块

新增目录：

```text
mylody/evidence/
  __init__.py
  types.py
  resolver.py
  provider_base.py
  provider_musicbrainz.py
  provider_lastfm.py
  bundle.py
```

职责：

- 规范化曲目信息。
- 查询外部元数据 API。
- 合并多个来源。
- 输出结构化 EvidenceBundle。
- 不负责写乐评。

### 6.3 Guardrails 模块

新增：

```text
mylody/ai/guardrails.py
```

第一版规则：

- 必须是 dict。
- 必须包含核心字段。
- `rating` 必须在 0-10。
- `similar_songs` 必须是 list。
- `schema_version` 必须是 `review_v2`。
- 当 `analysis_basis == "track_metadata"` 时，`background` / `musicology` 不得出现高风险事实断言。

高风险词示例：

```text
发行于 / 收录于 / 制作人 / 由...制作 / BPM / 调式 / 大调 / 小调 /
采样 / 获奖 / Billboard / 格莱美 / 排行榜 / 写于 / 创作于 /
真实经历 / 灵感来自 / 和声进行 / chord progression
```

注意：高风险词不是永远禁止，而是“没有证据时禁止”。

### 6.4 缓存模块

现有文件：

```text
mylody/cache/key.py
mylody/cache/manager.py
```

改造目标：

1. 缓存读取时检查 `review_json.schema_version`。
2. 旧缓存没有 `schema_version` 时视为 miss。
3. 后续 Evidence 接入后，缓存可增加 `evidence_version` 或 `evidence_hash`。

推荐第一版不改数据库结构，只从 `review_json` 内部读取版本。

### 6.5 前端展示

现有目录：

```text
web/
```

改造目标：

- 展示 `factuality_level`。
- 展示 `analysis_basis`。
- 展示 `known_facts`。
- 展示 `uncertain_facts`。
- 展示 `safety_notes`。
- 如果有 `evidence_sources`，展示来源链接。

前端文案建议：

```text
依据：仅基于曲目信息
可信度：元数据级
未确认信息：无外部证据支持的创作背景已省略
```

---

## 7. 分阶段实施计划

### Phase 1：一天内可完成的安全底座

目标：即使没有联网，也明显降低幻觉。

任务：

1. 重写 `SYSTEM_PROMPT`，建立事实边界。
2. 扩展 `ReviewData` 到 v2。
3. 添加 `schema_version = "review_v2"`。
4. 缓存读取检查 schema version。
5. 新增 `guardrails.py`。
6. AI 输出失败时 retry repair 一次。
7. 更新单元测试。

验收：

- 无证据时不写制作人、发行年份、BPM、采样、奖项。
- `pytest tests/test_prompt.py tests/test_ai_client.py` 通过。
- 旧缓存不再直接命中新版本。

### Phase 2：接入 MusicBrainz 元数据

目标：让部分歌曲进入 `external_evidence` 模式。

任务：

1. 新增 `EvidenceBundle` 数据结构。
2. 新增 `MusicBrainzProvider`。
3. 根据 title / artist / album 搜索候选 recording。
4. 做简单置信度评分。
5. 高置信度事实进入 `known_facts`。
6. 低置信度候选进入 `uncertain_facts`。
7. `build_user_prompt` 支持 evidence 输入。

验收：

- 对主流歌曲能返回 MusicBrainz 来源。
- 无法高置信匹配时，乐评仍可生成，但标记 `metadata_only`。
- evidence 来源可在 API 返回和前端看到。

### Phase 3：搜索 Agent 与 Writer 隔离

目标：如果接入通义、GLM、Mimo 等搜索模型，也不让它们直接写最终乐评。

任务：

1. 新增 `SearchProviderBase`。
2. 支持一种搜索型模型或搜索 API。
3. 搜索结果转为 EvidenceBundle。
4. Review Writer 只读取 EvidenceBundle。
5. 在缓存中记录 `evidence_hash`。

验收：

- 搜索结果可追溯到 URL。
- 乐评正文中的事实能在 evidence 中找到。
- writer model 关闭原生联网仍可工作。

### Phase 4：前端可信度展示

目标：让用户能看出乐评依据，不把 AI 输出当百科。

任务：

1. Review 卡片增加可信度标签。
2. 增加“已确认事实”区域。
3. 增加“未确认信息”区域。
4. 增加“资料来源”区域。
5. 对 `metadata_only` 乐评显示轻提示。

验收：

- 用户能区分“听感分析”和“事实背景”。
- 乐评没有变成免责声明，但边界清楚。

### Phase 5：回归测试集

目标：防止后续 prompt 越改越会编。

任务：

1. 建立 20 首歌测试集。
2. 覆盖热门歌、冷门歌、中文歌、欧美歌、同名歌、缺专辑歌。
3. 不真实调用 AI，只测试 guardrails。
4. 添加典型幻觉样本。

验收：

- 高风险断言会被测试拦截。
- schema 变更会触发测试失败。

---

## 8. DeepSeek 在本项目中的定位

当前项目使用 DeepSeek 时，建议走 OpenAI-compatible `custom` provider：

```yaml
ai:
  provider: "custom"
  api_key: "YOUR_DEEPSEEK_KEY"
  model: "deepseek-v4-flash"
  base_url: "https://api.deepseek.com"
```

建议定位：

- DeepSeek 作为 **Review Writer**。
- 不依赖 DeepSeek 自己完成联网搜索。
- 如果要搜索，由 Mylody 提供 Tool 或独立 Evidence Provider。
- 对 DeepSeek Provider 增加 JSON Output / Tool Calls 支持，但不要把 provider 逻辑写死进 AIClient。

短期可做：

```python
response = await client.chat.completions.create(
    model=self._model,
    messages=[...],
    response_format={"type": "json_object"},
    timeout=self._timeout,
)
```

注意：兼容接口不一定都支持 `response_format`，需要 try/fallback。

---

## 9. 推荐任务拆分

### Issue 1：Safe Review Prompt

标题：

```text
feat(ai): add safe review prompt with factual boundaries
```

范围：

- `mylody/ai/prompt.py`
- `tests/test_prompt.py`

### Issue 2：ReviewData v2

标题：

```text
feat(ai): add review factuality fields
```

范围：

- `mylody/types.py`
- `tests/test_ai_client.py`

### Issue 3：Guardrails + Retry Repair

标题：

```text
feat(ai): validate review output and retry repair once
```

范围：

- `mylody/ai/guardrails.py`
- `mylody/ai/client.py`
- `tests/test_guardrails.py`
- `tests/test_ai_client.py`

### Issue 4：Cache Version Isolation

标题：

```text
fix(cache): ignore old review cache without schema_version
```

范围：

- `mylody/cache/manager.py`
- `tests/test_cache_manager.py`

### Issue 5：MusicBrainz Evidence Provider

标题：

```text
feat(evidence): add MusicBrainz metadata provider
```

范围：

- `mylody/evidence/*`
- `requirements.txt`
- `tests/test_evidence_musicbrainz.py`

### Issue 6：Evidence-aware Prompt

标题：

```text
feat(ai): ground reviews with evidence bundle
```

范围：

- `mylody/ai/prompt.py`
- `mylody/ai/client.py`
- `tests/test_prompt.py`

### Issue 7：Frontend Factuality Display

标题：

```text
feat(web): show review factuality and evidence sources
```

范围：

- `web/index.html`
- `web/js/display.js`
- `web/css/review-card.css`

---

## 10. 最小可行版本

如果时间很紧，只做这 5 件：

1. Safe Review Prompt。
2. `ReviewData.schema_version = "review_v2"`。
3. 缓存读取检查 `schema_version`。
4. `guardrails.py` 拦截无证据高风险断言。
5. DeepSeek/OpenAI-compatible provider 增加 JSON output fallback。

这 5 件不依赖外部音乐 API，但能马上减少幻觉。

如果还能多做一件：

6. 接入 MusicBrainz，只做 title/artist/album 搜索和来源展示。

---

## 11. 最终目标

Mylody 不应该追求“AI 什么都知道”，而应该追求：

```text
AI 清楚哪些是已知事实，
哪些只是听感分析，
哪些信息没有证据，
并且仍然能写出好看的乐评。
```

