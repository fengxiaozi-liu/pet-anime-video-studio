# artifact-t2i-002: 即梦 (Jimeng) T2I Provider 实现

> 文件路径: `backend/app/providers/t2i/jimeng_t2i.py`

---

## 1. 概述

即梦是字节跳动旗下的 AI 图像生成产品，采用**异步模式**工作流：
1. `submit()` 提交生成任务，获得 `provider_task_id`
2. `poll()` 根据 `provider_task_id` 轮询任务状态，直至完成或失败

**Provider Code:** `jimeng` | **Display Name:** `即梦`

---

## 2. 架构位置

```
TextToImageProvider (ABC)
  ↑
  └── JimengT2IProvider  ← 即梦 Provider（异步模式）
```

| 方法 | 模式 | 说明 |
|------|------|------|
| `submit()` | ✅ 覆盖 | 真正向上游 POST 提交任务 |
| `poll()` | ✅ 覆盖 | 真正向上游 GET 轮询状态 |
| `_do_generate()` | ✅ 覆盖 | 返回失败（即梦不支持同步） |
| `generate()` | 继承默认 | 调用 `_do_generate()` → 返回 failed |
| `normalize_result()` | 继承默认 | 由 `poll()` 调用链处理 |

---

## 3. 配置字段 (`list_config_fields`)

| key | label | kind | required | 说明 |
|-----|-------|------|----------|------|
| `api_key` | API Key | password | ✅ | 即梦开放平台 Key |
| `base_url` | API Base URL | text | ✗ | 默认 `https://www.jimengjimeng.com` |
| `default_image_size` | 默认图像尺寸 | select | ✗ | 如 `1024x1024` |
| `default_style` | 默认风格 | select | ✗ | 如 `anime`、`photography` |
| `poll_interval_seconds` | 轮询间隔（秒） | text | ✗ | 默认 `3` |

### 支持的图像尺寸
- `1024x1024` (1:1)
- `768x1024` (3:4)
- `1024x768` (4:3)
- `768x1344` (9:16)
- `1344x768` (16:9)

### 支持的风格
`auto` / `photography` / `anime` / `oil_painting` / `watercolor` / `sketch` / `flat_illustration` / `chinese_painting` / `3d_render`

---

## 4. API 端点

### 提交任务
```
POST {base_url}/api/v2/image/generate
Headers: Authorization: Bearer {api_key}
Body: {"prompt": "...", "image_size": "...", "style": "...", ...}

成功响应:
{"request_id": "xxx", "status": "pending", "message": "任务已提交"}
```

### 轮询任务
```
GET {base_url}/api/v2/image/task/{task_id}
Headers: Authorization: Bearer {api_key}

进行中响应:
{"request_id": "xxx", "status": "processing", "progress": 50}

成功响应:
{"request_id": "xxx", "status": "success", "image_url": "https://..."}

失败响应:
{"request_id": "xxx", "status": "failed", "error": "内容违规"}
```

---

## 5. 状态映射

| 上游 `status` | `T2ITaskSubmission.normalized_status` | `T2IResult.normalized_status` |
|---------------|---------------------------------------|-------------------------------|
| `pending` | `submitted` | — |
| `processing` | — | `processing` |
| `success/done/completed` | — | `done` |
| `failed/error` | — | `failed` |

---

## 6. 代码骨架

```python
class JimengT2IProvider(TextToImageProvider):

    def code(self) -> str: return "jimeng"
    def display_name(self) -> str: return "即梦"
    def description(self) -> str: return "字节跳动即梦 AI 图像生成..."

    def list_config_fields(self) -> list[T2IProviderField]: ...

    def validate_config(self, config: dict) -> list[str]: ...

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_async": True,
            "supports_sync": False,   # 即梦仅支持异步
            "supports_styles": True,
            "supports_negative_prompt": True,
            "supports_image_size": True,
            "supported_image_sizes": [...],
            "supported_styles": [...],
        }

    # ── 异步模式 ────────────────────────────────

    def submit(self, *, prompt, ...) -> T2ITaskSubmission:
        # POST /api/v2/image/generate
        # 返回 T2ITaskSubmission(provider_task_id=request_id,
        #                         normalized_status="submitted")

    def poll(self, *, provider_task_id, config) -> T2IResult:
        # GET /api/v2/image/task/{task_id}
        # status=success → T2IResult(image_url=..., normalized_status="done")
        # status=processing → T2IResult(normalized_status="processing")
        # status=failed → T2IResult(normalized_status="failed")

    # ── 同步生成（不支持）──────────────────────

    def _do_generate(self, ...) -> T2IResult:
        return T2IResult(normalized_status="failed",
                         raw_response={"error": "Jimeng does not support sync..."})
```

---

## 7. 与 `_extract.py` 的关系

`poll()` 返回的 `T2IResult` 已包含 `image_url` / `image_b64`，因此：
- `normalize_result()` 会直接识别为 `done`（无需调用 `_extract.py`）
- 若 `poll()` 因网络错误返回空 `image_url`/`image_b64`，`normalize_result()` 才会尝试从 `raw_response` 中提取

---

## 8. 健康检查

`healthcheck()` 继承父类默认实现，基于 `validate_config()` 校验：
- 检查 `api_key` 非空且长度 >= 8
- 检查 `poll_interval_seconds` 为正数

---

## 9. 变更日志

| 日期 | 变更 |
|------|------|
| 2026-03-23 | 初始实现：完成 `submit()` / `poll()` / `validate_config()` / `list_config_fields()` / `get_capabilities()` |
