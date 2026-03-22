# Artifact: t2i-008 — T2I Provider 单元测试

**任务**: 为重构后的 T2I Provider 架构编写测试用例，覆盖所有 Provider
**时间**: 2026-03-23
**状态**: ✅ 完成

---

## 1. 测试文件

| 文件 | 行数 | 测试数量 | 覆盖内容 |
|------|------|---------|---------|
| `backend/tests/test_t2i_providers.py` | 554 | 73 | 所有 Provider 的核心接口 |
| `backend/tests/test_t2i_dispatcher.py` | 293 | 31 | T2IDispatcher 调度逻辑 |
| **合计** | **847** | **104** | |

---

## 2. 测试覆盖内容

### `test_t2i_providers.py` — 按测试类分组

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestProviderIdentity` | 8 | `code()` / `display_name()` / `description()` |
| `TestListConfigFields` | 10 | 各 Provider 字段数量、类型、必填检查 |
| `TestValidateConfig` | 14 | 合法/非法配置的校验 |
| `TestGetCapabilities` | 6 | 能力字典结构、异步/同步模式标志 |
| `TestHealthcheck` | 8 | 有效/无效配置的健康检查 |
| `TestGenerateInvalidConfig` | 8 | `generate()` 无效配置抛出 ValueError |
| `TestSubmitReturnsTaskSubmission` | 5 | `submit()` 返回 `T2ITaskSubmission` |
| `TestPollReturnsT2IResult` | 6 | `poll()` 返回 `T2IResult` |
| `TestNormalizeResult` | 3 | `normalize_result()` 状态归一化 |
| `TestT2IDataClasses` | 3 | `T2IResult` / `T2ITaskSubmission` / `T2IProviderField` 数据类 |
| **小计** | **73** | |

### `test_t2i_dispatcher.py` — 按测试类分组

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestT2IDispatcher` | 6 | `supported_codes()` / `list_providers()` |
| `TestDispatcherValidateProviderConfig` | 6 | 配置校验委托 |
| `TestDispatcherHealthcheck` | 3 | 健康检查委托 |
| `TestDispatcherGenerateRouting` | 4 | `generate()` 路由到正确 Provider |
| `TestDispatcherSubmitRouting` | 3 | `submit()` 路由到正确 Provider |
| `TestDispatcherPollRouting` | 3 | `poll()` 路由到正确 Provider |
| **小计** | **31** | |

---

## 3. 测试结果

```
============================= 104 passed in 4.80s ==============================
```

覆盖率（新增测试覆盖的模块）:
- `app/providers/t2i/base_t2i.py`: 91%
- `app/providers/t2i/dalle_t2i.py`: 86%
- `app/providers/t2i/sd_t2i.py`: 83%
- `app/providers/t2i/jimeng_t2i.py`: 76%
- `app/providers/t2i/tongyi_t2i.py`: 58%
- `app/providers/t2i/dispatcher.py`: 100%

---

## 4. 实现修复

### 4.1 `generate()` 添加配置校验

**文件**: `backend/app/providers/t2i/base_t2i.py`

**变更**: 在 `generate()` 方法调用 `_do_generate()` 之前，先调用 `validate_config()` 校验配置。若校验失败，抛出 `ValueError`。

**原因**: 原实现直接调用 `_do_generate()`，导致无效配置时抛出 `KeyError` 或其他非预期异常。

**Diff**:
```python
def generate(self, *, prompt, ... config, ...):
    # 新增：校验配置，失败则抛出 ValueError
    errors = self.validate_config(config)
    if errors:
        raise ValueError(f"Invalid config for provider {self.code()}: {'; '.join(errors)}")
    result = self._do_generate(...)
    return self.normalize_result(result)
```

---

## 5. 测试关键技术点

### 5.1 Mock HTTP 调用

使用 `unittest.mock.patch("urllib.request.urlopen")` mock 网络调用，确保测试不依赖真实 API：

```python
def _mock_response(self, response_data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp

def test_jimeng_submit_returns_task_submission(self, valid_jimeng_config):
    provider = JimengT2IProvider()
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = self._mock_response({"request_id": "task-123", "status": "pending"})
        submission = provider.submit(prompt="a cat", config=valid_jimeng_config)
        assert isinstance(submission, T2ITaskSubmission)
        assert submission.provider_task_id == "task-123"
```

### 5.2 异步 + 同步模式覆盖

- **异步 Provider** (jimeng): `submit()` → 返回 `T2ITaskSubmission`；`poll()` → 返回 `T2IResult`
- **同步 Provider** (dalle, sd): `submit()` → 调用 `generate()` 并包装；`poll()` → 返回失败
- **混合 Provider** (tongyi): 同时支持同步和异步

### 5.3 数据类完整性验证

```python
def test_t2i_result_to_dict(self):
    result = T2IResult(image_url="...", normalized_status="done", ...)
    d = result.to_dict()
    assert d["image_url"] == "..."

def test_t2i_provider_field_to_dict(self):
    field = T2IProviderField(key="api_key", label="API Key", required=True, ...)
    d = field.to_dict()
    assert d["required"] is True
```

---

## 6. 运行命令

```bash
cd backend
.venv/bin/pytest tests/test_t2i_providers.py tests/test_t2i_dispatcher.py -v

# 带覆盖率
.venv/bin/pytest tests/test_t2i_providers.py tests/test_t2i_dispatcher.py --cov=app/providers/t2i --cov-report=term-missing
```
