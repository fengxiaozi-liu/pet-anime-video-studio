# T2I Provider 实现文档：通义万相 (Tongyi Wanxiang)

## 概述

`TongyiWanxiangT2IProvider` 是基于 `TextToImageProvider` 基类的通义万相文生图 Provider 实现。

通义万相是阿里云旗下的 AI 图像生成服务，支持同步和异步两种模式。

## API 端点

| 模式 | 端点 | 方法 | 用途 |
|------|------|------|------|
| 同步 | `/api/v1/services/aigc/text2image/image-sync` | POST | 直接返回图片 |
| 异步提交 | `/api/v1/services/aigc/text2image/image-generation` | POST | 提交生成任务 |
| 异步轮询 | `/api/v1/services/aigc/text2image/image-generation/{task_id}` | GET | 查询任务状态 |

Base URL: `https://dashscope.aliyuncs.com`（默认）

## 配置字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `api_key` | password | 是 | - | 阿里云 DashScope API Key |
| `base_url` | text | 否 | `https://dashscope.aliyuncs.com` | API 服务地址 |
| `model` | select | 否 | `wanx2.1-t2i-plus` | 模型名 |
| `default_image_size` | select | 否 | - | 默认图像尺寸 |
| `default_style` | select | 否 | - | 默认风格 |
| `use_async` | select | 否 | `false` | 是否使用异步模式 |
| `poll_interval_seconds` | text | 否 | `3` | 异步轮询间隔 |

## 支持的尺寸

- `1024*1024` — 1:1 (1024×1024)
- `768*1024` — 3:4 (768×1024)
- `1024*768` — 4:3 (1024×768)
- `768*1344` — 9:16 (768×1344)
- `1344*768` — 16:9 (1344×768)

## 支持的风格

- `auto` — 自动
- `photography` — 摄影
- `anime` — 动漫
- `oil_painting` — 油画
- `watercolor` — 水彩
- `3d_render` — 3D 渲染

## 设计决策

### 1. 同步模式优先

默认使用同步模式（`use_async=false`），直接通过 `/image-sync` 端点返回图片结果。
同步模式更简单，适合大多数场景。

### 2. 异步模式降级

当 `use_async=false` 时，`submit()` 会自动降级为同步模式：
直接调用 `generate()`（即 `_do_generate()` + `normalize_result()`），并包装为已完成的任务提交记录。

### 3. 请求头 X-DashScope-Async

- 同步模式: `X-DashScope-Async: disable`
- 异步模式: `X-DashScope-Async: enable`

### 4. 响应提取

图片 URL 从 `output.image_url` 提取（通用），也支持 `output.url`。

### 5. 不支持 negative_prompt

通义万相同步 API 不直接支持 `negative_prompt` 参数，capabilities 中明确标注：
`supports_negative_prompt: False`。

### 6. 错误处理

- `HTTPError`: 返回 `http_error` 状态
- `URLError`: 返回 `url_error` 状态
- API 错误码/消息: 返回 `failed` 状态

## 方法实现摘要

| 方法 | 模式 | 说明 |
|------|------|------|
| `code()` | - | 返回 `"tongyi"` |
| `display_name()` | - | 返回 `"通义万相"` |
| `description()` | - | 返回 `"阿里云通义万相文生图 API"` |
| `list_config_fields()` | - | 返回 7 个配置字段 |
| `validate_config()` | - | 校验 api_key、base_url、poll_interval |
| `get_capabilities()` | - | 返回能力描述 |
| `_do_generate()` | 同步 | 调用 `/image-sync` 端点 |
| `submit()` | 异步 | 调用 `/image-generation` 端点，或降级同步 |
| `poll()` | 异步 | 调用 `/image-generation/{task_id}` 端点 |

## 使用示例

```python
from backend.app.providers.t2i import TongyiWanxiangT2IProvider

provider = TongyiWanxiangT2IProvider()

# 同步生成
result = provider.generate(
    prompt="A cute anime cat",
    style="anime",
    image_size="1024*1024",
    config={"api_key": "sk-xxx"},
)
print(result.image_url)

# 异步提交
submission = provider.submit(
    prompt="A cute anime cat",
    style="anime",
    config={"api_key": "sk-xxx", "use_async": "true"},
)
task_id = submission.provider_task_id

# 异步轮询
result = provider.poll(provider_task_id=task_id, config={"api_key": "sk-xxx"})
print(result.image_url)
```
