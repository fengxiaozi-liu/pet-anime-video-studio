"""
即梦 (Jimeng) T2I Provider

即梦是字节跳动旗下的 AI 图像生成产品，采用异步模式：
1. submit() 提交生成任务，返回 provider_task_id
2. poll() 根据 task_id 轮询任务状态，直至完成或失败

API 参考（典型格式）：
- 提交：POST /api/v2/image/generate
- 轮询：GET  /api/v2/image/task/{task_id}
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Any

from .base_t2i import (
    TextToImageProvider,
    T2IProviderField,
    T2IResult,
    T2ITaskSubmission,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JIMENG_BASE_URL = "https://www.jimengjimeng.com"

_SUBMIT_PATH = "/api/v2/image/generate"
_QUERY_PATH_TEMPLATE = "/api/v2/image/task/{task_id}"

# 即梦支持的标准图像尺寸
_JIMENG_IMAGE_SIZES = [
    {"label": "1:1 (1024×1024)", "value": "1024x1024"},
    {"label": "3:4 (768×1024)", "value": "768x1024"},
    {"label": "4:3 (1024×768)", "value": "1024x768"},
    {"label": "9:16 (768×1344)", "value": "768x1344"},
    {"label": "16:9 (1344×768)", "value": "1344x768"},
]

# 即梦支持的画面风格
_JIMENG_STYLES = [
    {"label": "通用", "value": "auto"},
    {"label": "摄影", "value": "photography"},
    {"label": "动漫", "value": "anime"},
    {"label": "油画", "value": "oil_painting"},
    {"label": "水彩", "value": "watercolor"},
    {"label": "素描", "value": "sketch"},
    {"label": "扁平插画", "value": "flat_illustration"},
    {"label": "国画", "value": "chinese_painting"},
    {"label": "建模渲染", "value": "3d_render"},
]


# ---------------------------------------------------------------------------
# Provider Implementation
# ---------------------------------------------------------------------------


class JimengT2IProvider(TextToImageProvider):
    """即梦 (Jimeng) T2I Provider — 异步模式"""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def code(self) -> str:
        return "jimeng"

    def display_name(self) -> str:
        return "即梦"

    def description(self) -> str:
        return "字节跳动即梦 AI 图像生成，支持多种风格和尺寸"

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
                placeholder="sk-xxx",
                help_text="即梦开放平台 API Key，可在即梦开放平台获取",
            ),
            T2IProviderField(
                key="base_url",
                label="API Base URL",
                kind="text",
                required=False,
                placeholder=_JIMENG_BASE_URL,
                help_text="即梦 API 服务地址，保留默认即可",
            ),
            T2IProviderField(
                key="default_image_size",
                label="默认图像尺寸",
                kind="select",
                required=False,
                options=_JIMENG_IMAGE_SIZES,
                help_text="生成图片的默认尺寸",
            ),
            T2IProviderField(
                key="default_style",
                label="默认风格",
                kind="select",
                required=False,
                options=_JIMENG_STYLES,
                help_text="生成图片的默认风格",
            ),
            T2IProviderField(
                key="poll_interval_seconds",
                label="轮询间隔（秒）",
                kind="text",
                required=False,
                placeholder="3",
                help_text="轮询任务状态的时间间隔，默认 3 秒",
            ),
        ]

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors = []
        if not config.get("api_key"):
            errors.append("缺少 API Key，请在配置中填写即梦 API Key")
        api_key = config.get("api_key", "")
        if api_key and len(api_key) < 8:
            errors.append("API Key 长度异常，请确认是否填写正确")
        # poll_interval 必须是正数
        poll_interval = config.get("poll_interval_seconds", "3")
        try:
            interval = float(poll_interval)
            if interval <= 0:
                errors.append("轮询间隔必须大于 0")
        except (TypeError, ValueError):
            errors.append("轮询间隔必须是数字")
        return errors

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_async": True,
            "supports_sync": False,  # 即梦仅支持异步模式
            "supports_styles": True,
            "supports_negative_prompt": True,
            "supports_image_size": True,
            "supported_image_sizes": [s["value"] for s in _JIMENG_IMAGE_SIZES],
            "supported_styles": [s["value"] for s in _JIMENG_STYLES],
            "max_image_size": "1344x768",
            "max_images_per_request": 1,
        }

    # ------------------------------------------------------------------
    # Async workflow
    # ------------------------------------------------------------------

    def submit(
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
    ) -> T2ITaskSubmission:
        """
        提交即梦图像生成任务。

        POST {base_url}/api/v2/image/generate
        Body: {"prompt": "...", "image_size": "...", "style": "...", ...}

        成功响应示例:
        {"request_id": "xxx", "status": "pending", "message": "任务已提交"}
        """
        base_url = config.get("base_url", _JIMENG_BASE_URL).rstrip("/")
        api_key = config["api_key"]

        # 构建请求体
        payload: dict[str, Any] = {
            "prompt": prompt,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if style:
            payload["style"] = style
        if image_size:
            payload["image_size"] = image_size
        elif config.get("default_image_size"):
            payload["image_size"] = config["default_image_size"]
        if num_images > 1:
            payload["n"] = num_images

        # 透传 extra_params（如 seed, quality 等）
        if extra_params:
            payload.update(extra_params)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}{_SUBMIT_PATH}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                raw_response: dict[str, Any] = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            raw_response = {"http_error": e.code, "body": e.read().decode("utf-8", errors="replace")}
            return T2ITaskSubmission(
                provider_task_id="",
                provider_status="http_error",
                normalized_status="failed",
                request_payload=payload,
                raw_response=raw_response,
            )
        except urllib.error.URLError as e:
            raw_response = {"url_error": str(e.reason)}
            return T2ITaskSubmission(
                provider_task_id="",
                provider_status="network_error",
                normalized_status="failed",
                request_payload=payload,
                raw_response=raw_response,
            )

        # 提取 request_id（即 provider_task_id）
        request_id = raw_response.get("request_id", "") or raw_response.get("id", "")
        status = raw_response.get("status", "pending")

        return T2ITaskSubmission(
            provider_task_id=str(request_id),
            provider_status=status,
            normalized_status="submitted",
            request_payload=payload,
            raw_response=raw_response,
        )

    def poll(
        self,
        *,
        provider_task_id: str,
        config: dict[str, Any],
    ) -> T2IResult:
        """
        轮询即梦任务状态。

        GET {base_url}/api/v2/image/task/{task_id}

        响应示例（进行中）:
        {"request_id": "xxx", "status": "processing", "progress": 50}

        响应示例（完成）:
        {"request_id": "xxx", "status": "success", "image_url": "https://..."}

        响应示例（失败）:
        {"request_id": "xxx", "status": "failed", "error": "内容违规"}
        """
        if not provider_task_id:
            return T2IResult(
                normalized_status="failed",
                raw_response={"error": "provider_task_id 为空"},
            )

        base_url = config.get("base_url", _JIMENG_BASE_URL).rstrip("/")
        api_key = config["api_key"]

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}{_QUERY_PATH_TEMPLATE.format(task_id=provider_task_id)}"

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                raw: dict[str, Any] = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            raw = {"http_error": e.code, "body": e.read().decode("utf-8", errors="replace")}
            return T2IResult(
                normalized_status="failed",
                raw_response=raw,
            )
        except urllib.error.URLError as e:
            raw = {"url_error": str(e.reason)}
            return T2IResult(
                normalized_status="failed",
                raw_response=raw,
            )

        status = raw.get("status", "").lower()
        error_msg = raw.get("error") or raw.get("message", "")

        # 已完成
        if status in ("success", "done", "completed"):
            image_url = raw.get("image_url") or raw.get("url") or ""
            image_b64 = raw.get("b64_json") or raw.get("image_b64") or ""

            return T2IResult(
                image_url=str(image_url) if image_url else None,
                image_b64=str(image_b64) if image_b64 else None,
                normalized_prompt=raw.get("prompt"),
                normalized_status="done",
                raw_response=raw,
            )

        # 失败
        if status in ("failed", "error"):
            return T2IResult(
                normalized_status="failed",
                raw_response=raw,
            )

        # 进行中（pending / processing / running 等）
        return T2IResult(
            normalized_status="processing",
            raw_response=raw,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_image_size(image_size: str | None) -> tuple[int, int]:
        """解析 'WIDTHxHEIGHT' 字符串，返回 (width, height)"""
        if not image_size:
            return 1024, 1024
        try:
            w, h = image_size.lower().split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            return 1024, 1024

    # ------------------------------------------------------------------
    # Sync generation — 不支持
    # ------------------------------------------------------------------

    def _do_generate(
        self,
        *,
        prompt: str,
        negative_prompt: str | None,
        style: str | None,
        style_strength: float | None,
        image_size: str | None,
        num_images: int,
        config: dict[str, Any],
        extra_params: dict[str, Any] | None,
    ) -> T2IResult:
        """
        即梦不支持同步生成，直接返回失败。
        请使用 submit() + poll() 异步模式。
        """
        return T2IResult(
            normalized_status="failed",
            raw_response={
                "error": "Jimeng does not support sync generation. "
                "Use submit() + poll() instead."
            },
        )
