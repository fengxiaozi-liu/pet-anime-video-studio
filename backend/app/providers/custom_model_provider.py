from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx

from .base import BaseProvider, ProviderField, ProviderTaskState, ProviderTaskSubmission, SceneTaskContext


SUPPORTED_CUSTOM_PROTOCOLS = {"openai", "anthropic"}


def is_custom_provider_code(provider_code: str) -> bool:
    return str(provider_code or "").startswith("custom:")


def custom_provider_fields() -> list[ProviderField]:
    return [
        ProviderField(
            "protocol",
            "协议类型",
            kind="select",
            required=True,
            options=[
                {"label": "OpenAI", "value": "openai"},
                {"label": "Anthropic", "value": "anthropic"},
            ],
        ),
        ProviderField("base_url", "URL", required=True, placeholder="https://example.com/generate"),
        ProviderField("api_key", "API Key", kind="password", required=True),
        ProviderField("model", "Model", required=True, placeholder="video-model-v1"),
    ]


def _openai_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return base


def _anthropic_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/messages"):
        return base
    if base.endswith("/v1"):
        return f"{base}/messages"
    return base


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part).strip()
    return ""


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型文本响应中未找到 JSON 对象")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("模型文本响应不是 JSON object")
    return payload


def _normalize_response_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("自定义视频助手返回结果必须是 JSON object")
    if raw.get("video_url"):
        return raw
    choices = raw.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = _extract_text_content(message.get("content"))
        if content:
            payload = _extract_json_object(content)
            if payload.get("video_url"):
                return payload
    content = raw.get("content")
    if content:
        text = _extract_text_content(content)
        if text:
            payload = _extract_json_object(text)
            if payload.get("video_url"):
                return payload
    raise ValueError("自定义视频助手返回缺少 video_url")


class CustomModelProvider(BaseProvider):
    def code(self) -> str:
        return "custom:model"

    def display_name(self) -> str:
        return "自定义视频助手"

    def description(self) -> str:
        return "通过自定义 URL / API Key / Model 调用外部视频生成服务。"

    def list_config_fields(self) -> list[ProviderField]:
        return custom_provider_fields()

    def validate_config(self, provider_config_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        protocol = str(provider_config_json.get("protocol") or "openai").strip().lower()
        base_url = str(provider_config_json.get("base_url") or "").strip()
        api_key = str(provider_config_json.get("api_key") or "").strip()
        model = str(provider_config_json.get("model") or "").strip()
        if protocol not in SUPPORTED_CUSTOM_PROTOCOLS:
            errors.append("protocol 必须是 openai 或 anthropic")
        if not base_url:
            errors.append("缺少 base_url")
        else:
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append("base_url 必须是合法的 http/https 地址")
        if not api_key:
            errors.append("缺少 api_key")
        if not model:
            errors.append("缺少 model")
        return errors

    def _build_prompt(self, scene: SceneTaskContext) -> str:
        parts: list[str] = []
        scene_prompt = str(scene.scene_payload.get("prompt") or scene.prompt or "").strip()
        story_summary = str(scene.storyboard.get("story_summary") or "").strip()
        style_prompt = str(scene.storyboard.get("style_prompt") or "").strip()
        if scene_prompt:
            parts.append(scene_prompt)
        if style_prompt:
            parts.append(f"style: {style_prompt}")
        if story_summary:
            parts.append(f"context: {story_summary}")
        return "\n".join(parts).strip()

    def _build_request(self, scene: SceneTaskContext, provider_config_json: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, Any]]:
        protocol = str(provider_config_json.get("protocol") or "openai").strip().lower()
        prompt = self._build_prompt(scene)
        base_url = str(provider_config_json["base_url"]).strip()
        reference_image_urls = [
            str(url or "").strip()
            for url in [
                scene.scene_payload.get("visual_asset_url"),
                *(scene.scene_payload.get("character_image_urls") or []),
            ]
            if str(url or "").strip()
        ]
        common_meta = {
            "job_id": scene.job_id,
            "scene_index": scene.scene_index,
            "scene": scene.scene_payload,
            "storyboard": scene.storyboard,
            "reference_image_urls": reference_image_urls,
        }
        if protocol == "anthropic":
            return (
                _anthropic_url(base_url),
                {
                    "x-api-key": str(provider_config_json["api_key"]),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                {
                    "model": provider_config_json["model"],
                    "system": "你是一个视频生成接口适配器。请返回严格 JSON，并包含 video_url 字段。",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    **common_meta,
                },
            )
        return (
            _openai_url(base_url),
            {
                "Authorization": f"Bearer {provider_config_json['api_key']}",
                "Content-Type": "application/json",
            },
            {
                "model": provider_config_json["model"],
                "messages": [
                    {"role": "system", "content": "你是一个视频生成接口适配器。请返回严格 JSON，并包含 video_url 字段。"},
                    {"role": "user", "content": prompt},
                ],
                **common_meta,
            },
        )

    def create_task(
        self,
        scene: SceneTaskContext,
        provider_config_json: dict[str, Any],
    ) -> ProviderTaskSubmission:
        errors = self.validate_config(provider_config_json)
        if errors:
            raise ValueError("；".join(errors))
        url, headers, payload = self._build_request(scene, provider_config_json)
        timeout = httpx.Timeout(120.0, connect=15.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            raw = response.json()
        normalized = _normalize_response_payload(raw)
        provider_task_id = str(normalized.get("task_id") or normalized.get("provider_task_id") or f"custom-{uuid.uuid4()}")
        provider_status = str(normalized.get("status") or normalized.get("provider_status") or "done")
        return ProviderTaskSubmission(
            provider_task_id=provider_task_id,
            provider_status=provider_status,
            normalized_status="submitted",
            request_url=url,
            get_url=url,
            request_payload=payload,
            raw_response=normalized,
        )

    def get_task(
        self,
        provider_task_id: str,
        provider_config_json: dict[str, Any],
        scene_job: dict[str, Any] | None = None,
    ) -> ProviderTaskState:
        raw = dict((scene_job or {}).get("provider_response_payload_json") or {})
        video_url = str(raw.get("video_url") or "").strip()
        if not video_url:
            raise ValueError("自定义视频助手未返回 video_url")
        return ProviderTaskState(
            provider_status=str(raw.get("status") or raw.get("provider_status") or "done"),
            normalized_status="succeeded",
            raw_response=raw,
            result_video_url=video_url,
            result_cover_url=str(raw.get("cover_url") or "").strip() or None,
        )
