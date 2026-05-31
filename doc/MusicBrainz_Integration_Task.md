# Codex 任务文档：为 Mylody 接入 MusicBrainz 音乐元信息数据库

## 目标

为 Mylody 实现 MusicBrainz 元信息接入能力，让后端可以根据歌曲名、艺术家名、专辑名获取可靠的音乐结构化信息，并将这些信息提供给 AI 乐评模块使用，降低 AI 对歌曲、艺术家、发行信息的幻觉。

本任务的目标不是让 AI 自己凭空搜索音乐资料，而是先通过 MusicBrainz 获取可信元数据，再把清洗后的结构化数据交给 AI。

---

## 背景

MusicBrainz 是开放音乐元信息数据库。我们需要接入的是 MusicBrainz Web Service 2。

基础接口：

```txt
https://musicbrainz.org/ws/2/
```

封面图接口使用 Cover Art Archive：

```txt
https://coverartarchive.org/
```

公开读取 MusicBrainz 数据目前不需要 API Key，但所有请求必须设置规范的 `User-Agent`。后端还必须实现限流和缓存，避免对 MusicBrainz 官方服务造成压力。

---

## 核心约束

### 1. 所有请求必须走后端

不要在前端直接请求 MusicBrainz。

原因：

* 统一设置 `User-Agent`
* 统一限流
* 统一缓存
* 避免暴露实现细节
* 方便后续替换数据源或增加商业支持配置

---

### 2. 必须设置 User-Agent

所有 MusicBrainz 请求都必须带请求头：

```txt
User-Agent: Mylody/0.1.0 ( jonywang317@gmail.com )
Accept: application/json
```

如果项目已有正式域名或联系页，之后可以改成：

```txt
User-Agent: Mylody/1.0.0 ( https://mylody.example.com/contact )
Accept: application/json
```

不要把 `User-Agent` 放在 URL 参数里，必须放在 HTTP headers 中。

---

### 3. 必须限流

MusicBrainz 主 API 请求必须限制为：

```txt
最多 1 request / second
```

实现要求：

* 后端全局共享一个 MusicBrainz 请求队列
* 所有 MusicBrainz 请求都通过同一个 wrapper
* 不允许多个接口绕过限流器直接请求 MusicBrainz
* 如果收到 503，视为被限流或服务不可用，应进行错误处理，不要疯狂重试

---

### 4. 必须缓存

不要每次用户搜索或打开歌曲页都重新请求 MusicBrainz。

建议缓存层级：

```txt
search query cache: 1 天
recording detail cache: 7 天或更久
release detail cache: 7 天或更久
cover art cache: 7 天或更久
```

如果当前项目还没有数据库，先做一个清晰的 repository/service 层接口，方便后续接入数据库。

---

## 推荐数据流

用户搜索歌曲时：

```txt
用户输入 song title / artist
        ↓
Mylody 后端 API
        ↓
查本地缓存
        ↓
缓存未命中，请求 MusicBrainz search recording
        ↓
返回候选 recording 列表
        ↓
用户选择或系统取最佳匹配
        ↓
根据 recording MBID 查询详情
        ↓
根据 release MBID 查询专辑 / 发行版本 / 封面
        ↓
清洗为 Mylody 内部 MusicMetadata
        ↓
保存缓存
        ↓
提供给 AI 乐评模块
```

---

## 需要实现的模块

建议新增以下文件。若项目目录结构不同，请按现有架构调整，但保持职责拆分。

```txt
src/lib/musicbrainz/client.ts
src/lib/musicbrainz/rateLimiter.ts
src/lib/musicbrainz/types.ts
src/lib/musicbrainz/mapper.ts
src/lib/musicbrainz/coverArt.ts
src/lib/musicbrainz/service.ts
src/app/api/music/search/route.ts
src/app/api/music/recording/[mbid]/route.ts
```

如果项目不是 Next.js App Router，请按项目现有后端路由方式实现等价接口。

---

## 类型设计

新增内部统一类型，不要直接把 MusicBrainz 原始 JSON 全量传给前端和 AI。

```ts
export type MusicMetadata = {
  recordingMbid: string;
  title: string;
  lengthMs?: number;

  artists: Array<{
    mbid?: string;
    name: string;
    sortName?: string;
    disambiguation?: string;
  }>;

  releases: Array<{
    mbid: string;
    title: string;
    date?: string;
    country?: string;
    status?: string;
    type?: string;
    barcode?: string;
    labelNames?: string[];
    coverArtUrl?: string;
    coverArtThumbnailUrl?: string;
  }>;

  isrcs?: string[];
  genres?: Array<{
    name: string;
    count?: number;
  }>;

  tags?: Array<{
    name: string;
    count?: number;
  }>;

  externalUrls?: Array<{
    type?: string;
    url: string;
  }>;

  source: "musicbrainz";
  fetchedAt: string;
};
```

搜索结果类型：

```ts
export type MusicSearchResult = {
  recordingMbid: string;
  title: string;
  score?: number;
  lengthMs?: number;
  artistCredit: string;
  firstReleaseDate?: string;
  releases?: Array<{
    mbid: string;
    title: string;
    date?: string;
    country?: string;
  }>;
};
```

---

## MusicBrainz Client

实现统一请求函数。

要求：

* 自动追加 `fmt=json`
* 自动设置 headers
* 所有请求经过限流器
* 对 404、503、非 2xx 状态做清晰错误处理
* 不在业务代码里散落 `fetch("https://musicbrainz.org/...")`

示例实现：

```ts
const MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2";

const USER_AGENT =
  process.env.MUSICBRAINZ_USER_AGENT ??
  "Mylody/0.1.0 ( jonywang317@gmail.com )";

export async function musicbrainzGet<T>(
  path: string,
  params: Record<string, string | number | undefined> = {}
): Promise<T> {
  const url = new URL(`${MUSICBRAINZ_BASE_URL}${path}`);

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  }

  url.searchParams.set("fmt", "json");

  return runMusicBrainzLimited(async () => {
    const response = await fetch(url.toString(), {
      headers: {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
      },
      next: {
        revalidate: 86400,
      },
    });

    if (response.status === 404) {
      throw new Error(`MusicBrainz resource not found: ${path}`);
    }

    if (response.status === 503) {
      throw new Error("MusicBrainz rate limit or service unavailable");
    }

    if (!response.ok) {
      throw new Error(`MusicBrainz request failed: ${response.status}`);
    }

    return response.json() as Promise<T>;
  });
}
```

---

## Rate Limiter

实现简单全局限流器。

```ts
let lastRequestAt = 0;
let queue = Promise.resolve();

export function runMusicBrainzLimited<T>(task: () => Promise<T>): Promise<T> {
  queue = queue.then(async () => {
    const now = Date.now();
    const elapsed = now - lastRequestAt;
    const waitMs = Math.max(0, 1100 - elapsed);

    if (waitMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, waitMs));
    }

    lastRequestAt = Date.now();
    return task();
  });

  return queue as Promise<T>;
}
```

注意：

* 这里用 `1100ms` 是为了保守地满足 1 request/sec。
* 如果项目部署在 serverless 多实例环境，这个内存限流只能保证单实例内限流。后续生产环境应升级为 Redis-based distributed rate limiter。
* 当前阶段可以先用单实例限流器完成 MVP。

---

## 搜索 Recording

实现函数：

```ts
export async function searchRecordings(input: {
  title: string;
  artist?: string;
  limit?: number;
}): Promise<MusicSearchResult[]> {
  const query = input.artist
    ? `recording:"${input.title}" AND artist:"${input.artist}"`
    : `recording:"${input.title}"`;

  const data = await musicbrainzGet<MusicBrainzRecordingSearchResponse>(
    "/recording/",
    {
      query,
      limit: input.limit ?? 10,
    }
  );

  return data.recordings.map(mapRecordingSearchResult);
}
```

对应请求示例：

```txt
GET /ws/2/recording/?query=recording:"Nude" AND artist:"Radiohead"&fmt=json&limit=10
```

---

## 查询 Recording 详情

实现函数：

```ts
export async function getRecordingMetadata(
  recordingMbid: string
): Promise<MusicMetadata> {
  const data = await musicbrainzGet<MusicBrainzRecordingDetail>(
    `/recording/${recordingMbid}`,
    {
      inc: "artist-credits+releases+release-groups+isrcs+genres+tags+ratings+url-rels",
    }
  );

  return mapRecordingDetailToMusicMetadata(data);
}
```

对应请求示例：

```txt
GET /ws/2/recording/{recording_mbid}?inc=artist-credits+releases+release-groups+isrcs+genres+tags+ratings+url-rels&fmt=json
```

需要提取：

* recording MBID
* title
* length
* artist-credit
* releases
* ISRC
* genres
* tags
* external URLs

---

## 查询 Release 详情

当 recording 返回 releases 后，应根据 release MBID 查询更完整的发行信息。

```ts
export async function getReleaseDetail(releaseMbid: string) {
  return musicbrainzGet<MusicBrainzReleaseDetail>(
    `/release/${releaseMbid}`,
    {
      inc: "artist-credits+labels+recordings+release-groups+media+genres+tags",
    }
  );
}
```

对应请求示例：

```txt
GET /ws/2/release/{release_mbid}?inc=artist-credits+labels+recordings+release-groups+media+genres+tags&fmt=json
```

需要提取：

* release title
* release date
* country
* status
* barcode
* labels
* media / tracklist
* release group
* genres / tags

---

## 查询 Cover Art

封面图不要从 MusicBrainz 主 API 获取，应使用 Cover Art Archive。

实现：

```ts
const COVER_ART_BASE_URL = "https://coverartarchive.org";

export async function getCoverArtForRelease(releaseMbid: string): Promise<{
  image?: string;
  thumbnail250?: string;
  thumbnail500?: string;
  thumbnail1200?: string;
} | null> {
  const response = await fetch(`${COVER_ART_BASE_URL}/release/${releaseMbid}`, {
    headers: {
      "Accept": "application/json",
    },
    next: {
      revalidate: 604800,
    },
  });

  if (response.status === 404) {
    return null;
  }

  if (response.status === 503) {
    throw new Error("Cover Art Archive rate limit or service unavailable");
  }

  if (!response.ok) {
    throw new Error(`Cover Art Archive request failed: ${response.status}`);
  }

  const data = await response.json();

  const front =
    data.images?.find((image: any) => image.front === true) ??
    data.images?.[0];

  if (!front) {
    return null;
  }

  return {
    image: front.image,
    thumbnail250: front.thumbnails?.["250"] ?? front.thumbnails?.small,
    thumbnail500: front.thumbnails?.["500"] ?? front.thumbnails?.large,
    thumbnail1200: front.thumbnails?.["1200"],
  };
}
```

对应请求示例：

```txt
GET https://coverartarchive.org/release/{release_mbid}
```

可选快速封面接口：

```txt
GET https://coverartarchive.org/release/{release_mbid}/front
GET https://coverartarchive.org/release/{release_mbid}/front-500
GET https://coverartarchive.org/release-group/{release_group_mbid}/front-500
```

推荐优先使用 JSON listing，因为可以自己选择 front image 和 thumbnail。

---

## 后端 API 设计

### 1. 搜索歌曲

```txt
GET /api/music/search?title={title}&artist={artist}
```

返回：

```ts
{
  results: MusicSearchResult[];
}
```

行为：

* 校验 `title` 不能为空
* artist 可选
* 先查缓存
* 缓存未命中时请求 MusicBrainz
* 返回最多 10 条候选
* 不要让 AI 自动猜唯一答案，前端可以让用户选择

---

### 2. 查询歌曲详情

```txt
GET /api/music/recording/{mbid}
```

返回：

```ts
{
  metadata: MusicMetadata;
}
```

行为：

* 校验 MBID 格式
* 先查缓存
* 缓存未命中时请求 MusicBrainz recording detail
* 对关联 release 查询补充信息
* 尝试获取 cover art
* 映射为 Mylody 内部 MusicMetadata

---

## 缓存 / 数据库建议

如果项目已有数据库，建议新增这些表或等价模型。

### musicbrainz_recordings

```txt
id
mbid unique
title
length_ms
artist_credit_text
isrcs json
genres json
tags json
external_urls json
raw_json json
fetched_at
created_at
updated_at
```

### musicbrainz_releases

```txt
id
mbid unique
title
date
country
status
barcode
label_names json
cover_art_url
cover_art_thumbnail_url
raw_json json
fetched_at
created_at
updated_at
```

### musicbrainz_search_cache

```txt
id
query_hash unique
title
artist
results_json
expires_at
created_at
updated_at
```

如果暂时不接数据库，可以先实现接口层：

```ts
export interface MusicMetadataRepository {
  getRecording(mbid: string): Promise<MusicMetadata | null>;
  saveRecording(metadata: MusicMetadata): Promise<void>;

  getSearchResults(queryHash: string): Promise<MusicSearchResult[] | null>;
  saveSearchResults(
    queryHash: string,
    results: MusicSearchResult[],
    ttlSeconds: number
  ): Promise<void>;
}
```

然后先用内存缓存或项目现有缓存方案实现。

---

## 给 AI 乐评模块的上下文格式

新增一个函数，把 MusicMetadata 转成 AI 可读上下文。

```ts
export function buildMusicReviewContext(metadata: MusicMetadata): string {
  const artistText = metadata.artists.map((artist) => artist.name).join(", ");

  const releaseText = metadata.releases
    .slice(0, 3)
    .map((release) => {
      return [
        release.title,
        release.date ? `date: ${release.date}` : undefined,
        release.country ? `country: ${release.country}` : undefined,
        release.labelNames?.length
          ? `labels: ${release.labelNames.join(", ")}`
          : undefined,
      ]
        .filter(Boolean)
        .join(" | ");
    })
    .join("\n");

  const genreText = metadata.genres
    ?.slice(0, 10)
    .map((genre) => genre.name)
    .join(", ");

  const tagText = metadata.tags
    ?.slice(0, 15)
    .map((tag) => tag.name)
    .join(", ");

  return `
MusicBrainz metadata:
- Title: ${metadata.title}
- Artists: ${artistText}
- Recording MBID: ${metadata.recordingMbid}
- ISRCs: ${metadata.isrcs?.join(", ") || "unknown"}
- Genres: ${genreText || "unknown"}
- Tags: ${tagText || "unknown"}

Related releases:
${releaseText || "unknown"}

Instruction:
Use this metadata as factual background. Do not invent release dates, labels, chart history, credits, or genre claims that are not supported by the provided metadata.
`.trim();
}
```

AI prompt 中应明确：

```txt
你可以基于元信息做审美分析，但不能编造 MusicBrainz 没有提供的事实。
如果元信息缺失，请说“资料不足”，不要猜。
```

---

## 错误处理要求

### 搜索无结果

返回：

```ts
{
  results: [],
  message: "No matching recording found from MusicBrainz."
}
```

不要让 AI 自己编一个结果。

---

### 404

含义：

* MBID 不存在
* release 没有封面
* 查询对象不存在

处理：

* 对 recording detail：返回 404 给业务方
* 对 cover art：返回 `coverArtUrl: undefined`，不要让整个歌曲详情失败

---

### 503

含义：

* 被限流
* 服务暂时不可用

处理：

* 不要立即多次重试
* 返回清晰错误
* 记录日志
* 后续可加入指数退避

---

### 数据缺失

MusicBrainz 不是每首歌都有完整标签、流派、封面、ISRC。

处理原则：

* 字段缺失时使用 `undefined` 或空数组
* 不要编默认值
* 不要把 unknown 写成确定事实

---

## 安全和质量要求

1. 不要把 MusicBrainz 原始响应直接给 AI。
2. 不要让前端直接请求 MusicBrainz。
3. 不要绕过限流器。
4. 不要在没有 MBID 时调用 lookup。
5. 不要假设第一个搜索结果一定正确。
6. 不要因为没有封面就让歌曲详情接口失败。
7. 不要在 AI prompt 中暗示模型可以补全未知事实。
8. 所有外部请求必须有错误处理。
9. 所有返回给前端的数据必须经过 mapper 清洗。
10. 所有 API route 必须有输入校验。

---

## 验收标准

完成后应满足：

* 可以通过 `/api/music/search?title=Nude&artist=Radiohead` 搜索到候选歌曲。
* 搜索结果包含 recording MBID、标题、艺术家、时长、候选 release。
* 可以通过 `/api/music/recording/{mbid}` 获取结构化 `MusicMetadata`。
* 详情数据包含 artist、release、ISRC、genres、tags、external URLs 等可用字段。
* 如果 release 有封面，可以返回 Cover Art Archive 的封面图或缩略图。
* 所有 MusicBrainz 请求都带 `User-Agent`。
* 所有 MusicBrainz 请求都经过 1 request/sec 限流。
* 重复搜索同一歌曲时优先命中缓存。
* 404、503、无结果时不会导致服务崩溃。
* AI 乐评模块可以拿到 `buildMusicReviewContext(metadata)` 的输出作为事实背景。

---

## 建议测试用例

### 搜索

```txt
GET /api/music/search?title=Nude&artist=Radiohead
GET /api/music/search?title=Bad%20Guy&artist=Billie%20Eilish
GET /api/music/search?title=Shape%20of%20You&artist=Ed%20Sheeran
```

### 详情

从搜索结果中取 `recordingMbid` 后调用：

```txt
GET /api/music/recording/{recordingMbid}
```

### 异常

```txt
GET /api/music/search?title=
GET /api/music/recording/not-a-valid-mbid
GET /api/music/recording/00000000-0000-0000-0000-000000000000
```

---

## 后续可扩展方向

本次先完成 MusicBrainz 接入。后续可以继续扩展：

* 接入 ListenBrainz 获取听歌趋势和用户维度数据
* 接入 AcousticBrainz 替代数据源或本地音频特征分析
* 接入 Genius / Musixmatch 等歌词来源，但要注意授权
* 做多数据源交叉验证，进一步降低 AI 乐评幻觉
* 为每条 AI 乐评保留 metadata snapshot，方便追溯事实来源

---

## 本次任务建议拆分为 GitHub Issues

### Issue 1：实现 MusicBrainz client 和限流器

范围：

* `client.ts`
* `rateLimiter.ts`
* User-Agent
* JSON 请求
* 503 / 404 错误处理

### Issue 2：实现 recording 搜索接口

范围：

* `searchRecordings`
* `/api/music/search`
* 搜索结果 mapper
* 输入校验

### Issue 3：实现 recording 详情接口

范围：

* `getRecordingMetadata`
* `/api/music/recording/[mbid]`
* release / genre / tag / ISRC / URL 映射

### Issue 4：实现 Cover Art Archive 接入

范围：

* `coverArt.ts`
* release cover art 查询
* no cover fallback
* thumbnail 选择

### Issue 5：实现缓存层

范围：

* search cache
* recording metadata cache
* release cache
* repository interface

### Issue 6：接入 AI 乐评上下文

范围：

* `buildMusicReviewContext`
* prompt 规则
* 禁止 AI 编造元信息
* 缺失信息处理

---

## Codex 执行要求

请先阅读项目现有目录结构和技术栈，不要盲目创建重复架构。

实现时请优先保持小 PR：

1. 先做 client + rate limiter。
2. 再做 search API。
3. 再做 detail API。
4. 再做 cover art。
5. 最后接 AI context。

每个 PR 需要在说明里写清楚：

* 关联 issue 编号
* 已完成部分
* 未完成部分
* 如何测试
* 是否影响现有功能

如果一个 PR 只完成 issue 的一部分，请在 PR 描述中明确说明，不要假装完成整个 issue。
