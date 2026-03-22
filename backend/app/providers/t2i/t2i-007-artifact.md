# Artifact: t2i-007 — T2IDispatcher 集成到 character_image_assistants.py

**任务**: 更新 `character_image_assistants.py` 使用新的 T2IDispatcher + Provider 架构
**时间**: 2026-03-23
**状态**: ✅ 完成

---

## 1. 集成方式

### 1.1 新增模块级变量

```python
# 延迟初始化的 T2IDispatcher 单例（避免循环导入）
_t2i_dispatcher: "T2IDispatcher | None" = None

def _get_t2i_dispatcher() -> "T2IDispatcher":
    global _t2i_dispatcher
    if _t2i_dispatcher is None:
        from .providers.t2i.dispatcher import T2IDispatcher
        _t2i_dispatcher = T2IDispatcher()
    return _t2i_dispatcher
```

### 1.2 新增辅助函数

```python
def _get_provider_code(assistant_config: dict[str, Any]) -> str:
    """从 assistant_config.provider 提取 provider code，默认 'tongyi'"""
    provider = assistant_config.get("provider")
    if provider and str(provider).strip():
        return str(provider).strip().lower()
    return "tongyi"

def _is_t2i_mode(assistant_config: dict[str, Any]) -> bool:
    """判断是否走 T2I Provider 路径（而非 LLM 直接出图）"""
    provider = assistant_config.get("provider")
    if not provider or not str(provider).strip():
        return False
    try:
        codes = _get_t2i_dispatcher().supported_codes()
    except Exception:
        return False
    return str(provider).strip().lower() in codes
```

### 1.3 T2I Provider 路径 (`generate_character_preview` 内部)

当 `_is_t2i_mode()` 返回 `True` 时：

```python
if _is_t2i_mode(assistant_config):
    provider_code = _get_provider_code(assistant_config)
    provider_config = {
        k: v for k, v in assistant_config.items()
        if k in ("api_key", "base_url", "model", "default_image_size",
                 "default_style", "use_async", "poll_interval_seconds")
    }
    style = visual_style_name or str(assistant_config.get("default_style", ""))

    t2i_result = _get_t2i_dispatcher().generate(
        provider_code=provider_code,
        prompt=prompt,
        config=provider_config,
        style=style,
        image_size=assistant_config.get("default_image_size"),
    )

    # T2IResult → 原有返回值格式
    if t2i_result.image_url:
        return {
            "preview_image_url": _cache_preview_url(storage_service, preview_url=t2i_result.image_url, filename_hint=filename_hint),
            "normalized_prompt": t2i_result.normalized_prompt or prompt,
        }
    if t2i_result.image_b64:
        image_bytes = base64.b64decode(t2i_result.image_b64)
        return {
            "preview_image_url": _save_temp_preview(storage_service, image_bytes=image_bytes, extension=".png", filename_hint=filename_hint),
            "normalized_prompt": t2i_result.normalized_prompt or prompt,
        }
```

---

## 2. 接口变更

### 2.1 `validate_character_image_assistant_config(config)`

**变更**: 新增 `type="t2i"` 分支

| type | 行为 |
|------|------|
| `"t2i"` | 调用 `T2IDispatcher.validate_provider_config(provider_code, provider_config)` |
| `"llm"` / 默认 | 原有 LLM 配置校验逻辑（protocol/base_url/api_key/model） |

**向后兼容**: 不传 `type` 或 `type="llm"` → 原有校验逻辑完全不变。

### 2.2 `generate_character_preview(..., assistant_config)`

**变更**: 新增 T2I Provider 路由分支

| assistant_config.provider | 行为 |
|---------------------------|------|
| `null` / `""` / 未设置 | 走原有 LLM 直接出图逻辑（OpenAI/Anthropic） |
| `"tongyi"` / `"jimeng"` / `"dalle"` / `"sd"` | 走 `T2IDispatcher.generate()` |

**外部调用方**: 接口签名完全不变，调用方无需修改。

---

## 3. 向后兼容策略

1. **provider 未设置**: 默认走原有 LLM 路径，完全不感知 T2I 调度器。
2. **provider 设置为未知值**: 走 LLM 路径（`_is_t2i_mode` 内部检查 `supported_codes()`）。
3. **T2IDispatcher 初始化失败**: 静fallback 到 LLM 路径，`_is_t2i_mode` 捕获异常返回 `False`。
4. **T2I Provider 出图失败**: 抛出 `ValueError`，错误信息包含 provider_code 和原始异常。

---

## 4. 配置映射

| assistant_config 字段 | → Provider config 字段 | 说明 |
|----------------------|------------------------|------|
| `api_key` | `api_key` | Provider API Key |
| `base_url` | `base_url` | API 端点（可选，有默认值） |
| `model` | `model` | 模型名称 |
| `default_image_size` | `default_image_size` | 默认图像尺寸 |
| `default_style` | `default_style` | 默认风格 |
| `use_async` | `use_async` | 异步模式（通义万相） |
| `poll_interval_seconds` | `poll_interval_seconds` | 轮询间隔（通义万相） |

---

## 5. 文件变更摘要

| 文件 | 变更类型 |
|------|---------|
| `backend/app/character_image_assistants.py` | 重构：新增 T2I 路由、辅助函数、更新 `validate_character_image_assistant_config` |
| `backend/app/providers/t2i/t2i-007-artifact.md` | 新增：本文档 |

---

## 6. 测试验证要点

- [ ] `provider=null` → 走 LLM 路径（原有行为不变）
- [ ] `provider="tongyi"` → 走通义万相 Provider
- [ ] `provider="jimeng"` → 走即梦 Provider
- [ ] `provider="dalle"` → 走 DALL-E Provider
- [ ] `provider="sd"` → 走 Stable Diffusion Provider
- [ ] `type="t2i"` 配置校验走 Provider 校验逻辑
- [ ] `type="llm"` 配置校验走原有 LLM 校验逻辑
- [ ] T2I 返回 `image_url` 时正确缓存到 storage
- [ ] T2I 返回 `image_b64` 时正确解码保存
- [ ] T2I 出图失败时抛出含 provider_code 的 `ValueError`
