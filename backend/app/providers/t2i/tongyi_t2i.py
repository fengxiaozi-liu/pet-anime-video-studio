"""
通义万相 (Tongyi Wanxiang) T2I Provider

通义万相是阿里云旗下的 AI 图像生成服务，支持同步和异步两种模式：
- 同步模式：直接返回图片结果（默认）
- 异步模式：submit() 提交任务，poll() 轮询状态

API 参考：
- 同步：POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-sync
- 异步：POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-generation
- 轮询：GET  https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-generation/{task_id}
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
    T2ITaskSubmission,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"

_SYNC_PATH = "/api/v1/services/aigc/text2image/image-sync"
_ASYNC_SUBMIT_PATH = "/api/v1/services/aigc/text2image/image-generation"
_ASYNC_QUERY_TEMPLATE = "/api/v1/services/aigc/text2image/image-generation/{task_id}"

_TONGYI_MODELS = [
    {"label": "wanx2.1-t2i-plus", "value": "wanx2.1-t2i-plus"},
    {"label": "wanx2.0-t2i-pro", "value": "wanx2.0-t2i-pro"},
]

_TONGYI_IMAGE_SIZES = [
    {"label": "1:1 (1024x1024)", "value": "1024*1024"},
    {"label": "3:4 (768x1024)", "value": "768*1024"},
    {"label": "4:3 (1024x768)", "value": "1024*768"},
    {"label": "9:16 (768x1344)", "value": "768*1344"},
    {"label": "16:9 (1344x768)", "value": "1344*768"},
]

_TONGYI_STYLES = [
    {"label": "auto", "value": "auto"},
    {"label": "photography", "value": "photography"},
    {"label": "anime", "value": "anime"},
    {"label": "oil_painting", "value": "oil_painting"},
    {"label": "watercolor", "value": "watercolor"},
    {"label": "3d_render", "value": "3d_render"},
]


# ---------------------------------------------------------------------------
# Provider Implementation
# ---------------------------------------------------------------------------


class TongyiWanxiangT2IProvider(TextToImageProvider):
    """通义万相 (Tongyi Wanxiang) T2I Provider — 同步模式（默认），支持异步模式"""

    def code(self) -> str:
        return "tongyi"

    def display_name(self) -> str:
        return "通义万相"

    def description(self) -> str:
        return "阿里云通义万相文生图 API"

    def list_config_fields(self) -> list[T2IProviderField]:
        return [
            T2IProviderField(
                key="api_key",
                label="API Key",
                kind="password",
                required=True,
                placeholder="sk-...",
                help_text="阿里云 DashScope API Key，可在阿里云百炼平台获取",
            ),
            T2IProviderField(
                key="base_url",
                label="API Base URL",
                kind="text",
                required=False,
                placeholder=_DASHSCOPE_BASE_URL,
                help_text="通义万相 API 服务地址，保留默认即可",
            ),
            T2IProviderField(
                key="model",
                label="模型",
                kind="select",
                required=False,
                options=_TONGYI_MODELS,
                help_text="通义万相文生图模型，默认 wanx2.1-t2i-plus",
            ),
            T2IProviderField(
                key="default_image_size",
                label="默认图像尺寸",
                kind="select",
                required=False,
                options=_TONGYI_IMAGE_SIZES,
                help_text="生成图片的默认尺寸",
            ),
            T2IProviderField(
                key="default_style",
                label="默认风格",
                kind="select",
                required=False,
                options=_TONGYI_STYLES,
                help_text="生成图片的默认风格",
            ),
            T2IProviderField(
                key="use_async",
                label="使用异步模式",
                kind="select",
                required=False,
                options=[
                    {"label": "否（同步模式，默认）", "value": "false"},
                    {"label": "是（异步模式）", "value": "true"},
                ],
                help_text="同步模式直接返回图片；异步模式通过 submit+poll 提交并轮询任务",
            ),
            T2IProviderField(
                key="poll_interval_seconds",
                label="轮询间隔（秒）",
                kind="text",
                required=False,
                placeholder="3",
                help_text="异步模式轮询任务状态的时间间隔，默认 3 秒",
            ),
        ]

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors = []
        if not config.get("api_key"):
            errors.append("缺少 API Key，请在配置中填写阿里云 DashScope API Key")
        api_key = config.get("api_key", "")
        if api_key and len(api_key) < 8:
            errors.append("API Key 长度异常，请确认是否填写正确")
        base_url = config.get("base_url", _DASHSCOPE_BASE_URL).strip()
        if base_url and not (
            base_url.startswith("https://") or base_url.startswith("http://")
        ):
            errors.append("Base URL 必须以 http:// 或 https:// 开头")
        poll_interval = config.get("poll_interval_seconds", "3")
        try:
            interval = float(poll_interval)
            if interval <= 0:
                errors.append("轮询间隔必须大于 0")
        except (TypeError, ValueError):
            errors.append("轮询间隔必须是数字")
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_async": True,
            "supports_sync": True,
            "supports_styles": True,
            "supports_negative_prompt": False,
            "supports_image_size": True,
            "supported_image_sizes": [s["value"] for s in _TONGYI_IMAGE_SIZES],
            "supported_styles": [s["value"] for s in _TONGYI_STYLES],
            "max_image_size": "1344*768",
            "max_images_per_request": 1,
        }

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
        base_url = config.get("base_url", _DASHSCOPE_BASE_URL).rstrip("/")
        api_key = config["api_key"]
        model = config.get("model", "wanx2.1-t2i-plus")

        parameters: dict[str, Any] = {}
        if style:
            parameters["style"] = style
        elif config.get("default_style"):
            parameters["style"] = config["default_style"]

        if image_size:
            parameters["size"] = image_size
        elif config.get("default_image_size"):
            parameters["size"] = config["default_image_size"]

        if extra_params:
            for k, v in extra_params.items():
                if k not in ("size", "style", "model"):
                    parameters[k] = v

        payload: dict[str, Any] = {
            "model": model,
            "input": {"prompt": prompt},
        }
        if parameters:
            payload["parameters"] = parameters

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-DashScope-Async": "disable",
        }

        url = f"{base_url}{_SYNC_PATH}"
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

        output = raw_response.get("output", {})
        image_url = output.get("image_url") or output.get("url") or ""

        if image_url:
            return T2IResult(
                image_url=str(image_url),
                normalized_prompt=prompt,
                normalized_status="done",
                raw_response=raw_response,
            )

        code = raw_response.get("code", "")
        message = raw_response.get("message", "")
        if code or message:
            return T2IResult(normalized_status="failed", raw_response=raw_response)

        return T2IResult(normalized_status="failed", raw_response=raw_response)

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
        if config.get("use_async", "false") != "true":
            return self._submit_sync(
                prompt=prompt,
                negative_prompt=negative_prompt,
                style=style,
                style_strength=style_strength,
                image_size=image_size,
                num_images=num_images,
                config=config,
                extra_params=extra_params,
            )

        base_url = config.get("base_url", _DASHSCOPE_BASE_URL).rstrip("/")
        api_key = config["api_key"]
        model = config.get("model", "wanx2.1-t2i-plus")

        parameters: dict[str, Any] = {}
        if style:
            parameters["style"] = style
        elif config.get("default_style"):
            parameters["style"] = config["default_style"]

        if image_size:
            parameters["size"] = image_size
        elif config.get("default_image_size"):
            parameters["size"] = config["default_image_size"]

        if extra_params:
            for k, v in extra_params.items():
                if k not in ("size", "style", "model"):
                    parameters[k] = v

        payload: dict[str, Any] = {
            "model": model,
            "input": {"prompt": prompt},
        }
        if parameters:
            payload["parameters"] = parameters

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-DashScope-Async": "enable",
        }

        url = f"{base_url}{_ASYNC_SUBMIT_PATH}"
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

        request_id = raw_response.get("request_id", "")
        status = raw_response.get("status", "submitted")

        return T2ITaskSubmission(
            provider_task_id=str(request_id),
            provider_status=status,
            normalized_status="submitted",
            request_payload=payload,
            raw_response=raw_response,
        )

    def _submit_sync(
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
        result = self.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            style_strength=style_strength,
            image_size=image_size,
            num_images=num_images,
            config=config,
            extra_params=extra_params,
        )
        return T2ITaskSubmission(
            provider_task_id=f"sync-{self.code()}-{id(result)}",
            provider_status="done",
            normalized_status=result.normalized_status,
            request_payload={"prompt": prompt},
            raw_response=result.raw_response,
        )

    def poll(
        self,
        *,
        provider_task_id: str,
        config: dict[str, Any],
    ) -> T2IResult:
        if not provider_task_id:
            return T2IResult(
                normalized_status="failed",
                raw_response={"error": "provider_task_id 为空"},
            )

        base_url = config.get("base_url", _DASHSCOPE_BASE_URL).rstrip("/")
        api_key = config["api_key"]

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}{_ASYNC_QUERY_TEMPLATE.format(task_id=provider_task_id)}"

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                raw: dict[str, Any] = json.loads(resp_body)
        except urllib.error.HTTPError as e:
            raw = {"http_error": e.code, "body": e.read().decode("utf-8", errors="replace")}
            return T2IResult(normalized_status="failed", raw_response=raw)
        except urllib.error.URLError as e:
            raw = {"url_error": str(e.reason)}
            return T2IResult(normalized_status="failed", raw_response=raw)

        status = raw.get("status", "").upper()
        output = raw.get("output", {})

        if status in ("SUCCEEDED", "SUCCESS", "DONE", "COMPLETED"):
            image_url = output.get("image_url") or output.get("url") or ""
            return T2IResult(
                image_url=str(image_url) if image_url else None,
                normalized_prompt=output.get("prompt"),
                normalized_status="done",
                raw_response=raw,
            )

        if status in ("FAILED", "ERROR"):
            return T2IResult(normalized_status="failed", raw_response=raw)

        return T2IResult(normalized_status="processing", raw_response=raw)
