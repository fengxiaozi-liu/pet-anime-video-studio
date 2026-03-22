# T2IDispatcher 设计文档 (t2i-006)

## 概述

`T2IDispatcher` 是 T2I Provider 子系统的统一入口，负责根据 `provider_code` 将请求路由到对应的 Provider 实例，并对外暴露一致的接口。

## 架构图

```
Client
  │
  ▼
T2IDispatcher
  │
  ├── provider_code="jimeng"  → JimengT2IProvider (async)
  ├── provider_code="tongyi"  → TongyiWanxiangT2IProvider (async/sync)
  ├── provider_code="dalle"   → DallET2IProvider (sync)
  └── provider_code="sd"     → StableDiffusionT2IProvider (sync)
```

## 调度策略

### generate() — 同步生成

```
Client.generate(provider_code="jimeng", ...)
  → T2IDispatcher.generate()
  → JimengT2IProvider.generate()
  → JimengT2IProvider._do_generate()
  → JimengT2IProvider.normalize_result()
  → T2IResult
```

直接透传所有参数给 Provider.execute()，最终返回 `T2IResult`。

### submit() — 异步提交

```
Client.submit(provider_code="tongyi", ...)
  → T2IDispatcher.submit()
  → TongyiWanxiangT2IProvider.submit()
  → T2ITaskSubmission(provider_task_id, normalized_status="submitted")
```

内部直接调用 `Provider.submit()`，由 Provider 自己判断走 submit 还是 generate（基类默认实现 submit → generate）。

### poll() — 异步轮询

```
Client.poll(provider_code="tongyi", provider_task_id="xxx", ...)
  → T2IDispatcher.poll()
  → TongyiWanxiangT2IProvider.poll()
  → T2IResult
```

同步模式 Provider（dalle/sd）的 `poll()` 默认返回失败结果，因为它们的 submit() 已同步返回完整结果。

## 设计决策

### 1. 单例 Provider 实例

`_PROVIDER_INSTANCES` 缓存已创建的 Provider 实例，避免重复初始化（如加载模型、检查配置等）。线程安全由 Python GIL 保证。

### 2. submit() 的默认行为

基类 `TextToImageProvider.submit()` 默认实现为：
```python
def submit(self, ...):
    result = self.generate(...)  # 同步调用
    return T2ITaskSubmission(provider_task_id=f"sync-{code}-{id(result)}", ...)
```

这使得同步模式 Provider（dalle/sd）无需覆盖 submit()，但返回的 `normalized_status="done"`，调用方无需再 poll()。

### 3. 异步模式 Provider 的 poll() 覆盖

即梦、通义万相等异步 Provider 覆盖了 `poll()`，真正向上游轮询任务状态直至完成或失败。

### 4. validate_provider_config()

校验逻辑委托给对应 Provider 的 `validate_config()`，保持职责单一。

### 5. list_providers()

返回所有 Provider 的 metadata，供前端动态渲染 Provider 列表、配置表单等。

## Provider 能力矩阵

| Provider  | supports_async | supports_sync | 备注 |
|-----------|----------------|---------------|------|
| jimeng    | ✅              | ✅             | 即梦，异步优先 |
| tongyi    | ✅              | ✅             | 通义万相，两种模式皆支持 |
| dalle     | ❌ (默认走sync) | ✅             | DALL-E，同步返回 |
| sd        | ❌ (默认走sync) | ✅             | Stable Diffusion，同步返回 |

## 文件路径

- 调度器：`backend/app/providers/t2i/dispatcher.py`
- 导出：`backend/app/providers/t2i/__init__.py`
- Artifact：`backend/app/providers/t2i/t2i-006-artifact.md`
