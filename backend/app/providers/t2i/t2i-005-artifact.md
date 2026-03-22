# t2i-005 Artifact — Stable Diffusion T2I Provider 实现

## 概述

本 artifact 记录 **Stable Diffusion T2I Provider** 的实现细节，对应任务 `t2i-005`。

---

## 实现文件

| 文件 | 路径 |
|------|------|
| Provider 实现 | `backend/app/providers/t2i/sd_t2i.py` |
| 模块导出 | `backend/app/providers/t2i/__init__.py` |

---

## 设计决策（Key Design Decisions）

### 1. 同步模式（Sync-only）

Stable Diffusion（SD WebUI / ComfyUI / SDForge）均为同步 API：
- 调用 `POST /sdapi/v1/txt2img` 后，服务器**同步完成生图**并直接返回 base64 数据
- 无需任务提交 + 轮询的两阶段流程
- 因此 `supports_async=False`，`supports_sync=True`

这与 DALL-E Provider 的设计保持一致。

### 2. API 端点选择

采用 **SD WebUI 兼容模式**（`/sdapi/v1/txt2img`），这是最广泛使用的自托管 SD API 协议。

ComfyUI 使用 `/prompt` 提交 + `/history/{prompt_id}` 查询的异步模式，不符合 SD 通用场景。

### 3. 认证策略

- `api_key` 定义为**可选**字段
- 原因：本地部署的 SD WebUI 通常无认证；云端 SDForge 等服务可能需要 `Bearer` 认证
- `validate_config()` 仅在校验 api_key 非空时检查长度

### 4. 配置字段设计

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `base_url` | text | ✅ | `http://localhost:7860` | SD 服务地址 |
| `api_key` | password | ❌ | `None` | Bearer Token 认证 |
| `model` | text | ❌ | `None` | SD 模型 checkpoint 名称 |
| `image_size` | select | ❌ | `1024x1024` | 输出尺寸 |
| `steps` | number | ❌ | `30` | 采样步数 |
| `guidance_scale` | number | ❌ | `7.5` | CFG Scale |
| `sampler_name` | select | ❌ | `Euler a` | 采样算法 |

### 5. `override_settings` 注入模型名

当用户指定 `model` 字段时，通过 `override_settings.sd_model_checkpoint` 动态切换模型，而非在请求 URL 中指定。这是 SD WebUI 官方推荐的运行时模型切换方式。

### 6. `extra_params` 透传

支持透传 `enable_hr`（高清修复）、`denoising_strength`（重绘强度）等高级参数，不影响主流程。

### 7. 超时设置

`urllib.request.urlopen(timeout=300)` — 300 秒超时，SD 生图可能需要较长时间（尤其是高分辨率）。

---

## API 契约

### 端点

```
POST {base_url}/sdapi/v1/txt2img
```

### 请求头

```
Content-Type: application/json
Authorization: Bearer {api_key}   # 可选
```

### 请求体

```json
{
  "prompt": "a cute cat",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "cfg_scale": 7.5,
  "sampler_name": "Euler a",
  "override_settings": {
    "sd_model_checkpoint": "stable-diffusion-xl-base-1.0"
  }
}
```

### 响应

```json
{
  "images": ["base64_encoded_image_data..."],
  "parameters": { ... },
  "info": "{...}"
}
```

---

## 与其他 Provider 的差异

| 特性 | DALL-E | Stable Diffusion |
|------|--------|-----------------|
| API 类型 | OpenAI 官方 | 自托管 WebUI |
| 认证 | 必须 API Key | 可选 |
| 默认 base_url | `https://api.openai.com` | `http://localhost:7860` |
| 响应格式 | `data[0].url` / `b64_json` | `images[0]` base64 |
| negative_prompt | ❌ 不支持 | ✅ 支持 |
| sampler 选择 | ❌ 不支持 | ✅ 支持 |
| 模型动态切换 | ❌ 不支持 | ✅ via override_settings |

---

## 测试建议

1. **本地 SD WebUI 启动后**：配置 `base_url=http://localhost:7860`，测试生图
2. **认证场景**：配置 `api_key` 测试 SDForge 等云服务
3. **模型切换**：填写 `model=your-custom-model.safetensors`，验证 `override_settings` 生效
4. **参数校验**：steps=0、guidance_scale=50 等边界值测试

---

## 依赖

- Python 标准库：`json`, `urllib.request`, `urllib.error`，**无需额外依赖**
