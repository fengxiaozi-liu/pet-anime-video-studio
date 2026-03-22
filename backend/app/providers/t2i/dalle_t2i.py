"""
OpenAI DALL-E T2I Provider

DALL-E 是 OpenAI 的同步模式文生图 API：
- 直接调用 POST /v1/images/generations 获取结果
- 返回 image_url 或 b64_json
- 无需轮询

API 参考：
- 端点：POST https://api.openai.com/v1/images/generations
- Header: Authorization: Bearer {api_key}
- Body: {"model": "dall-e-3", "prompt": "...", "size": "1024x1024", "quality": "standard"}
- 响应：{"data": [{"url": "https://...", "b64_json": "..."}]}
"""

from __future__ import annotations

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

_DEFAULT_OPENAI_URL = "https://api.openai.com"
_GENERATIONS_PATH = "/v1/images/generations"

_DALLE_MODELS = [
    {"label": "dall-e-3 (默认)", "value": "dall-e-3"},
    {"label": "dall-e-2", "value": "dall-e-2"},
]

_DALLE_SIZES = [
    {"label": "1024x1024 (默认)", "value": "1024x1024"},
    {"label": "1024x1792 (竖版)", "value": "1024x1792"},
    {"label": "1792x1024 (横版)", "value": "1792x1024"},
]

_DALLE_QUALITIES = [
    {"label": "standard (默认)", "value": "standard"},
    {"label": "hd (更高细节)", "value": "hd"},
]


# ---------------------------------------------------------------------------
# Provider Implementation
# ---------------------------------------------------------------------------


class DallET2IProvider(TextToImageProvider):
    """OpenAI DALL-E T2I Provider — 同步模式"""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def code(self) -> str:
        return "dalle"

    def display_name(self) -> str:
        return "DALL-E"

    def description(self) -> str:
        return "OpenAI DALL-E 图像生成 API"

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def list_config_fields(self) -> list[T2IProviderField]:
        return [
            T2IProviderField(
                key="api_key",
                label="API Key",
                kind="password",
                required=True,
                placeholder="sk-...",
                help_text="OpenAI API Key，可在 OpenAI 平台获取",
            ),
            T2IProviderField(
                key="model",
                label="模型",
                kind="select",
                required=False,
                options=_DALLE_MODELS,
                help_text="DALL-E 模型版本，默认 dall-e-3",
            ),
            T2IProviderField(
                key="size",
                label="图像尺寸",
                kind="select",
                required=False,
                options=_DALLE_SIZES,
                help_text="生成图片的尺寸，默认 1024x1024",
            ),
            T2IProviderField(
                key="quality",
                label="图片质量",
                kind="select",
                required=False,
                options=_DALLE_QUALITIES,
                help_text="图片质量，dall-e-3 支持 standard/hd，默认 standard",
            ),
            T2IProviderField(
                key="base_url",
                label="API Base URL",
                kind="text",
                required=False,
                placeholder=_DEFAULT_OPENAI_URL,
                help_text="OpenAI API 服务地址，保留默认即可；可填写代理地址",
            ),
        ]

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors = []
        if not config.get("api_key"):
            errors.append("缺少 API Key，请在配置中填写 OpenAI API Key")
        api_key = config.get("api_key", "")
        if api_key and not api_key.startswith("sk-"):
            errors.append("API Key 必须以 sk- 开头，请确认是否填写正确")
        base_url = config.get("base_url", "").strip()
        if base_url and not (
            base_url.startswith("https://") or base_url.startswith("http://")
        ):
            errors.append("Base URL 必须以 http:// 或 https:// 开头")
        return errors

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_async": False,  # DALL-E 是同步模式，无需轮询
            "supports_sync": True,
            "supports_styles": False,
            "supports_negative_prompt": False,
            "supports_image_size": True,
            "supported_image_sizes": [s["value"] for s in _DALLE_SIZES],
            "supported_models": [m["value"] for m in _DALLE_MODELS],
            "supported_qualities": [q["value"] for q in _DALLE_QUALITIES],
            "max_image_size": "1792x1024",
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
        调用 OpenAI Images API（POST /v1/images/generations）。

        DALL-E API 请求格式：
        POST {base_url}/v1/images/generations
        Header: Authorization: Bearer {api_key}, Content-Type: application/json
        Body: {"model": "dall-e-3", "prompt": "...", "size": "1024x1024", "quality": "standard", "n": 1}

        成功响应示例：
        {"created": 1234567890, "data": [{"url": "https://...", "revised_prompt": "..."}]}

        b64_json 响应示例（当 response_format=b64_json 时）：
        {"created": 1234567890, "data": [{"b64_json": "...", "revised_prompt": "..."}]}
        """
        base_url = config.get("base_url", _DEFAULT_OPENAI_URL).rstrip("/")
        api_key = config["api_key"]
        model = config.get("model", "dall-e-3")
        size = image_size or config.get("size", "1024x1024")
        quality = config.get("quality", "standard")

        # DALL-E 仅支持 n=1（API 限制）
        n = 1

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n,
        }

        # 透传 extra_params（response_format 等）
        if extra_params:
            for k, v in extra_params.items():
                if k not in ("model", "prompt", "size", "quality", "n"):
                    payload[k] = v

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}{_GENERATIONS_PATH}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_body = resp.read().decode("utf-8")
                raw_response: dict[str, Any] = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            raw_response = {"http_error": e.code, "body": e.read().decode("utf-8", errors="replace")}
            return T2IResult(normalized_status="failed", raw_response=raw_response)
        except urllib.error.URLError as e:
            raw_response = {"url_error": str(e.reason)}
            return T2IResult(normalized_status="failed", raw_response=raw_response)

        # 解析响应
        data_list = raw_response.get("data", [])
        if not data_list:
            return T2IResult(
                normalized_status="failed",
                raw_response=raw_response,
            )

        first = data_list[0]
        image_url = first.get("url") or ""
        image_b64 = first.get("b64_json") or ""
        revised_prompt = first.get("revised_prompt")

        if image_url or image_b64:
            return T2IResult(
                image_url=str(image_url) if image_url else None,
                image_b64=str(image_b64) if image_b64 else None,
                normalized_prompt=revised_prompt or prompt,
                normalized_status="done",
                raw_response=raw_response,
            )

        # 无有效图片数据
        error_msg = raw_response.get("error", {}).get("message", "") if isinstance(raw_response.get("error"), dict) else raw_response.get("error", "")
        return T2IResult(
            normalized_status="failed",
            raw_response=raw_response,
        )
