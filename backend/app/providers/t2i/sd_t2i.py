"""
Stable Diffusion T2I Provider

Stable Diffusion 通常以自托管方式部署（ComfyUI / SD WebUI / SDForge 等），
通过 Web API 提供服务。标准 SD WebUI 支持 `POST /sdapi/v1/txt2img` 端点，
同步返回 base64 编码的图片数据，属于同步模式 Provider。

API 参考（SD WebUI）：
- 端点：POST {base_url}/sdapi/v1/txt2img
- Header: Content-Type: application/json
- Body: {"prompt": "...", "negative_prompt": "...", "width": 1024, "height": 1024,
          "steps": 30, "cfg_scale": 7.5, "sampler_name": "Euler a", ...}
- 响应：{"images": ["base64..."], "parameters": {...}, "info": "..."}

ComfyUI 兼容 API（ComfyUI API Workfow）：
- 端点：POST {base_url}/prompt
- 通过历史记录获取图片
（本案基于 SD WebUI 兼容模式实现）
"""

from __future__ import annotations

import base64
import json
import urllib.request
import urllib.error
from typing import Any

from .base_t2i import (
    TextToImageProvider,
    T2IProviderField,
    T2IResult,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_SD_URL = "http://localhost:7860"
_TXT2IMG_PATH = "/sdapi/v1/txt2img"

_SD_SAMPLERS = [
    {"label": "Euler a (默认)", "value": "Euler a"},
    {"label": "Euler", "value": "Euler"},
    {"label": "DPM++ 2M Karras", "value": "DPM++ 2M Karras"},
    {"label": "DPM++ SDE Karras", "value": "DPM++ SDE Karras"},
    {"label": "DDIM", "value": "DDIM"},
    {"label": "PLMS", "value": "PLMS"},
]

_SD_SIZES = [
    {"label": "512x512", "value": "512x512"},
    {"label": "768x768", "value": "768x768"},
    {"label": "1024x1024 (默认)", "value": "1024x1024"},
    {"label": "1024x768 (横版)", "value": "1024x768"},
    {"label": "768x1024 (竖版)", "value": "768x1024"},
]


# ---------------------------------------------------------------------------
# Provider Implementation
# ---------------------------------------------------------------------------


class StableDiffusionT2IProvider(TextToImageProvider):
    """Stable Diffusion T2I Provider — 同步模式（自托管 API）"""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def code(self) -> str:
        return "sd"

    def display_name(self) -> str:
        return "Stable Diffusion"

    def description(self) -> str:
        return "Stable Diffusion 本地或自托管 API"

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def list_config_fields(self) -> list[T2IProviderField]:
        return [
            T2IProviderField(
                key="base_url",
                label="API Base URL",
                kind="text",
                required=True,
                placeholder=_DEFAULT_SD_URL,
                help_text="SD WebUI/ComfyUI 等服务的地址，如 http://localhost:7860",
            ),
            T2IProviderField(
                key="api_key",
                label="API Key（可选）",
                kind="password",
                required=False,
                placeholder="留空表示无需认证",
                help_text="部分 SD 服务需要认证（如 SDForge），无需认证时留空",
            ),
            T2IProviderField(
                key="model",
                label="模型名称（可选）",
                kind="text",
                required=False,
                placeholder="stable-diffusion-xl-base-1.0",
                help_text="SD 模型名称，如 stable-diffusion-xl-base-1.0、v1-5-pruned-emaonly.safetensors",
            ),
            T2IProviderField(
                key="image_size",
                label="图像尺寸",
                kind="select",
                required=False,
                options=_SD_SIZES,
                help_text="生成图片的宽高，默认 1024x1024",
            ),
            T2IProviderField(
                key="steps",
                label="采样步数",
                kind="number",
                required=False,
                placeholder="30",
                help_text="采样步数，默认 30。值越大细节越多，速度越慢",
            ),
            T2IProviderField(
                key="guidance_scale",
                label="引导强度",
                kind="number",
                required=False,
                placeholder="7.5",
                help_text="CFG Scale，默认 7.5。值越大越严格遵循提示词",
            ),
            T2IProviderField(
                key="sampler_name",
                label="采样器",
                kind="select",
                required=False,
                options=_SD_SAMPLERS,
                help_text="采样算法，默认 Euler a",
            ),
        ]

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors = []
        base_url = config.get("base_url", "").strip()
        if not base_url:
            errors.append("缺少 API Base URL，请在配置中填写 SD 服务地址")
        if base_url and not (
            base_url.startswith("https://") or base_url.startswith("http://")
        ):
            errors.append("Base URL 必须以 http:// 或 https:// 开头")
        api_key = config.get("api_key", "").strip()
        if api_key and len(api_key) < 8:
            errors.append("API Key 长度不能少于 8 个字符，请确认是否填写正确")
        # 校验 steps
        steps = config.get("steps")
        if steps is not None:
            try:
                s = int(steps)
                if s < 1 or s > 500:
                    errors.append("采样步数应在 1~500 之间")
            except (ValueError, TypeError):
                errors.append("采样步数必须是整数")
        # 校验 guidance_scale
        cfg = config.get("guidance_scale")
        if cfg is not None:
            try:
                c = float(cfg)
                if c < 0 or c > 30:
                    errors.append("引导强度应在 0~30 之间")
            except (ValueError, TypeError):
                errors.append("引导强度必须是数字")
        return errors

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_async": False,  # SD 是同步模式，无需轮询
            "supports_sync": True,
            "supports_styles": False,
            "supports_negative_prompt": True,  # SD 原生支持 negative_prompt
            "supports_image_size": True,
            "supported_image_sizes": [s["value"] for s in _SD_SIZES],
            "supported_samplers": [s["value"] for s in _SD_SAMPLERS],
            "max_image_size": "1024x1024",
            "max_images_per_request": 1,
        }

    # ------------------------------------------------------------------
    # Sync generation
    # ------------------------------------------------------------------

    def _do_generate(
        self,
        *,
        prompt: str,
        negative_prompt: str | None = None,
        style: str | None = None,
        style_strength: float | None = None,
        image_size: str | None = None,
        num_images: int = 1,
        config: dict[str, Any],
        extra_params: dict[str, Any] | None = None,
    ) -> T2IResult:
        """
        调用 Stable Diffusion WebUI API（POST /sdapi/v1/txt2img）。

        SD WebUI API 请求格式：
        POST {base_url}/sdapi/v1/txt2img
        Header: Content-Type: application/json
                 Authorization: Bearer {api_key}  (如果有认证)

        Body 示例：
        {
            "prompt": "a cute cat",
            "negative_prompt": "blurry, low quality",
            "width": 1024,
            "height": 1024,
            "steps": 30,
            "cfg_scale": 7.5,
            "sampler_name": "Euler a"
        }

        成功响应示例：
        {
            "images": ["base64_encoded_image_data..."],
            "parameters": {
                "prompt": "a cute cat",
                "negative_prompt": "blurry, low quality",
                ...
            },
            "info": "..."
        }
        """
        base_url = config.get("base_url", _DEFAULT_SD_URL).rstrip("/")
        api_key = config.get("api_key", "").strip() or None

        # 解析 image_size
        width, height = self._parse_image_size(image_size, config)

        # 采样参数
        steps = self._parse_int(config.get("steps"), default=30)
        cfg_scale = self._parse_float(config.get("guidance_scale"), default=7.5)
        sampler_name = config.get("sampler_name", "Euler a")
        model = config.get("model", "").strip() or None

        payload: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
        }

        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if model:
            payload["override_settings"] = {"sd_model_checkpoint": model}

        # 透传 extra_params（如 enable_hr, denoising_strength 等）
        if extra_params:
            for k, v in extra_params.items():
                if k not in payload and k not in ("prompt", "negative_prompt"):
                    payload[k] = v

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{base_url}{_TXT2IMG_PATH}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=300) as resp:
                resp_body = resp.read().decode("utf-8")
                raw_response: dict[str, Any] = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            raw_response = {
                "http_error": e.code,
                "body": e.read().decode("utf-8", errors="replace"),
            }
            return T2IResult(normalized_status="failed", raw_response=raw_response)
        except urllib.error.URLError as e:
            raw_response = {"url_error": str(e.reason)}
            return T2IResult(normalized_status="failed", raw_response=raw_response)

        # 解析图片
        images = raw_response.get("images", [])
        if not images:
            return T2IResult(
                normalized_status="failed",
                raw_response=raw_response,
            )

        image_b64 = images[0] if images else ""

        if image_b64:
            return T2IResult(
                image_b64=str(image_b64),
                normalized_prompt=prompt,
                normalized_status="done",
                raw_response=raw_response,
            )

        return T2IResult(
            normalized_status="failed",
            raw_response=raw_response,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_image_size(
        self, image_size: str | None, config: dict[str, Any]
    ) -> tuple[int, int]:
        """解析 image_size 为 (width, height)"""
        size = image_size or config.get("image_size", "1024x1024")
        if "x" in size:
            parts = size.split("x", 1)
            try:
                w, h = int(parts[0]), int(parts[1])
                return w, h
            except ValueError:
                pass
        return 1024, 1024

    @staticmethod
    def _parse_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
