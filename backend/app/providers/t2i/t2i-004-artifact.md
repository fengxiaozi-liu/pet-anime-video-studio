# Artifact t2i-004: OpenAI DALL-E T2I Provider 实现

## 概述

| 字段 | 值 |
|------|-----|
| task_id | t2i-004 |
| artifact_id | artifact-t2i-004 |
| 类型 | file |
| 路径 | `backend/app/providers/t2i/dalle_t2i.py` |
| 创建时间 | 2026-03-23T03:32:00+08:00 |
| status | completed |

## 实现摘要

### 类名
`DallET2IProvider`

### 父类
`TextToImageProvider`（ABC）

### 工作模式
**同步模式**（sync-only）。DALL-E API 是同步阻塞调用，直接返回图片 URL 或 b64_json，无需提交+轮询。

### 架构决策

#### 1. 为什么只需实现 `_do_generate()`
DALL-E Images API 是**同步 REST 调用**：
```
POST /v1/images/generations
→ 等待处理完成
→ 直接返回 {data: [{url: "..."}]} 或 {data: [{b64_json: "..."}]}
```
这与即梦/通义的异步 submit+poll 模式完全不同，所以只需实现 `_do_generate()`，基类的 `submit()` 默认实现会自动调用 `generate()`（即 `_do_generate()` + `normalize_result()`）并包装为已完成的任务。

#### 2. `supports_async=False` 覆盖
基类 `get_capabilities()` 默认 `supports_async=True`。DALL-E 是同步模式，必须覆盖为 `False`，以便调度器知道不应调用 submit+poll 流程。

#### 3. `num_images` 被强制为 1
DALL-E API 的 `n` 参数只接受 1（API 限制），所以代码中 `n = 1` 硬编码，不使用传入的 `num_images` 参数。

#### 4. `negative_prompt` 和 `style` 参数被忽略
DALL-E API 原生不支持这两个参数，属于设计约束，不是 bug。

#### 5. 支持 `base_url` 可选配置
默认 `https://api.openai.com`，但用户可以填写代理地址，适配特殊网络环境。

### API 调用详情

```
端点：POST {base_url}/v1/images/generations
Header：
  Content-Type: application/json
  Authorization: Bearer {api_key}
Body：
  {
    "model": "dall-e-3" | "dall-e-2",
    "prompt": "...",
    "size": "1024x1024" | "1024x1792" | "1792x1024",
    "quality": "standard" | "hd",  # 仅 dall-e-3
    "n": 1
  }
```

### 响应解析

成功响应 `{data: [{url: "...", revised_prompt: "..."}]}` → `image_url` = url
成功响应 `{data: [{b64_json: "...", revised_prompt: "..."}]}` → `image_b64` = b64_json
失败响应 → `normalized_status = "failed"`

### 字段定义

| 字段 key | 类型 | 必填 | 默认值 | 说明 |
|---------|------|------|--------|------|
| api_key | password | ✅ | — | OpenAI API Key |
| model | select | ❌ | dall-e-3 | 模型版本 |
| size | select | ❌ | 1024x1024 | 图像尺寸 |
| quality | select | ❌ | standard | 图片质量 |
| base_url | text | ❌ | https://api.openai.com | API 地址 |

### Capabilities

```python
{
    "supports_async": False,   # 同步模式，无需轮询
    "supports_sync": True,
    "supports_styles": False,
    "supports_negative_prompt": False,
    "supports_image_size": True,
    "supported_image_sizes": ["1024x1024", "1024x1792", "1792x1024"],
    "supported_models": ["dall-e-3", "dall-e-2"],
    "supported_qualities": ["standard", "hd"],
    "max_image_size": "1792x1024",
    "max_images_per_request": 1,
}
```

### validate_config 校验规则

1. `api_key` 必须存在
2. `api_key` 必须以 `sk-` 开头
3. `base_url`（若填写）必须以 `http://` 或 `https://` 开头

### 与其他 Provider 的关键差异

| 特性 | 即梦 | 通义万相 | DALL-E |
|------|------|----------|--------|
| 模式 | 异步 | 同步+异步 | 同步 |
| supports_async | True | True | **False** |
| supports_sync | False | True | **True** |
| 需要轮询 | ✅ | ❌（同步） | ❌ |
| 支持 style | ✅ | ✅ | ❌ |
| 支持 negative_prompt | ✅ | ❌ | ❌ |
| 模型参数 | 无 | wanx2.1-t2i-plus | dall-e-3 / dall-e-2 |

## 导出

```python
from backend.app.providers.t2i import DallET2IProvider
```
