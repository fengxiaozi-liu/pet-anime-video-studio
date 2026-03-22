# T2I Provider 基类设计文档 (artifact-t2i-001)

> 文件路径: `backend/app/providers/t2i/base_t2i.py`

---

## 1. 设计决策 (Key Design Decisions)

### 1.1 父子类架构
- **父类** `TextToImageProvider` (ABC) 定义统一接口和默认行为
- **子类** 实现 `_do_generate()` 即可完成同步模式 Provider；异步模式 Provider 额外覆盖 `submit()` + `poll()`
- 不要求子类继承 dataclass，降低耦合

### 1.2 状态字段归一化
- `T2IResult` 新增 `normalized_status: str = "pending"` 字段
- `T2ITaskSubmission` 有独立的 `normalized_status: str = "submitted"` 字段
- 两者语义不同：`T2IResult.normalized_status` 表示图片是否成功生成；`T2ITaskSubmission.normalized_status` 表示任务所处阶段

### 1.3 同步 vs 异步 Provider
| 方法 | 同步 Provider（如 DALL-E、SD） | 异步 Provider（即梦、通义万相） |
|------|-------------------------------|-------------------------------|
| `_do_generate()` | ✅ 实现真正的 API 调用 | 可选覆盖 |
| `generate()` | 继承默认实现 | 可选覆盖 |
| `submit()` | 继承默认（调用 generate 包装结果） | ✅ 覆盖：真正提交任务 |
| `poll()` | 继承默认（返回 failed） | ✅ 覆盖：真正轮询任务 |

### 1.4 normalize_result() 的职责
- 若 `image_url` / `image_b64` 已非空 → 构造新 T2IResult，`normalized_status="done"`
- 若两者都空 → 调用 `_extract.py` 的 `extract_image_from_response()` 尝试从 `raw_response` 提取
  - 提取成功 → `normalized_status="done"`
  - 提取失败 → `normalized_status="failed"`
- 始终保留原始 `raw_response`，便于调试

### 1.5 T2IProviderField vs ProviderField
- `T2IProviderField` 是 T2I 模块独立的 dataclass，与通用 `ProviderField` 解耦
- 两者的 `to_dict()` 签名一致，可互相转换

---

## 2. 类结构

### 2.1 Data Classes

```
T2IProviderField (frozen dataclass)
├── key: str
├── label: str
├── kind: str = "text"
├── required: bool = False
├── placeholder: str | None = None
├── help_text: str | None = None
├── options: list[dict[str,str]] | None = None
└── to_dict() → dict

T2IResult (frozen dataclass)
├── image_url: str | None = None
├── image_b64: str | None = None
├── normalized_prompt: str | None = None
├── normalized_status: str = "pending"   ← 新增
└── raw_response: dict[str, Any] = field(default_factory=dict)

T2ITaskSubmission (frozen dataclass)
├── provider_task_id: str
├── provider_status: str
├── normalized_status: str = "submitted"
├── request_payload: dict[str, Any]
└── raw_response: dict[str, Any]
```

### 2.2 TextToImageProvider ABC 方法清单

| 方法 | 类型 | 说明 |
|------|------|------|
| `code()` | 抽象 | Provider 唯一标识 |
| `display_name()` | 抽象 | 用户可见名称 |
| `description()` | 抽象 | 简短描述 |
| `list_config_fields()` | 抽象 | 返回配置字段列表 |
| `validate_config()` | 抽象 | 校验配置，返回错误列表 |
| `get_capabilities()` | 具体 | 返回能力描述 dict（子类可覆盖） |
| `healthcheck()` | 具体 | 基于 validate_config（子类可覆盖） |
| `generate()` | 具体 | 调用 `_do_generate()` + `normalize_result()` |
| `submit()` | 具体 | 同步模式默认调用 `generate()` 包装结果 |
| `poll()` | 具体 | 同步模式默认返回 `failed` T2IResult |
| `_do_generate()` | 具体（虚） | 抛出 `NotImplementedError`（子类必须覆盖） |
| `normalize_result()` | 具体（虚） | 归一化 image_url/image_b64 并设置 status |

---

## 3. 方法调用链

### 同步模式（默认）

```
caller
  └─> generate(prompt, config, ...)
         ├─> _do_generate(...)  ← 子类实现
         │     返回 T2IResult(image_url=None, raw_response=api_response)
         └─> normalize_result(raw_result)
               ├─> raw_result.image_url 已非空 → T2IResult(status="done")
               └─> raw_result.image_url 为空
                     └─> extract_image_from_response(raw_response)
                           ├─> 找到图片 → T2IResult(status="done")
                           └─> 未找到 → T2IResult(status="failed")
```

### 异步模式（submit + poll）

```
caller
  └─> submit(prompt, config, ...)
         ├─> 真正向上游提交任务（子类覆盖实现）
         └─> T2ITaskSubmission(provider_task_id="xxx", status="submitted")

caller (轮询)
  └─> poll(provider_task_id, config)
         ├─> 真正向上游轮询（子类覆盖实现）
         └─> T2IResult(image_url="...", normalized_status="done")
```

---

## 4. 使用示例（子类实现骨架）

```python
from backend.app.providers.t2i.base_t2i import (
    TextToImageProvider,
    T2IProviderField,
    T2IResult,
)


class DallET2IProvider(TextToImageProvider):
    """同步模式 Provider 示例"""

    def code(self) -> str:
        return "dalle"

    def display_name(self) -> str:
        return "DALL-E"

    def description(self) -> str:
        return "OpenAI DALL-E 图像生成"

    def list_config_fields(self) -> list[T2IProviderField]:
        return [
            T2IProviderField("api_key", "API Key", kind="password", required=True),
        ]

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if not config.get("api_key"):
            errors.append("缺少 api_key")
        return errors

    def _do_generate(self, *, prompt, negative_prompt, style, style_strength,
                     image_size, num_images, config, extra_params) -> T2IResult:
        # 调用 OpenAI Images API
        response = call_dalle_api(prompt, api_key=config["api_key"], ...)
        return T2IResult(
            image_url=response["data"][0]["url"],
            raw_response=response,
        )
```

---

## 5. 与 _extract.py 的关系

- `_extract.py` 提供 `extract_image_from_response(data: dict) -> dict[str, str]`
- 支持字段：嵌套路径 (`data.url`, `data[0].url`)、base64 字段、data URI 等
- `normalize_result()` 在 `image_url`/`image_b64` 都为空时调用
- 子类如能直接设置 `image_url`/`image_b64`，则 `normalize_result()` 直接返回 `status="done"`

---

## 6. 变更日志

| 日期 | 变更 |
|------|------|
| 初始版本 | 完成 ABC 定义 + dataclass |
| 本次修复 | 1. 新增 `T2IResult.normalized_status` 字段<br>2. `normalize_result()` 正确设置 `normalized_status`<br>3. 清理未使用的 import (`Path`, `ProviderField`, `TYPE_CHECKING`)<br>4. `poll()` 默认实现返回正确的 `T2IResult`（含 `normalized_status="failed"`）<br>5. `T2IResult.to_dict()` 包含 `normalized_status` |
