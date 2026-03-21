from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


DEFAULT_CHARACTER_IMAGE_SYSTEM_PROMPT = """
你是一个角色形象设计助手。请根据角色名称、角色描述和故事背景，为角色出图服务补全更完整的中文提示词。

如果你返回文本，必须是严格 JSON，结构如下：
{
  "normalized_prompt": "适合角色出图模型的完整提示词",
  "preview_image_url": "可直接访问的角色预览图 URL"
}

如果上游接口本身直接返回图片 URL 或 base64 图片，也允许直接返回，不必强行包装成文本。
""".strip()

SUPPORTED_CHARACTER_IMAGE_PROTOCOLS = {"openai", "anthropic"}


def validate_character_image_assistant_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    protocol = str(config.get("protocol") or "openai").strip().lower()
    base_url = str(config.get("base_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    model = str(config.get("model") or "").strip()
    if protocol not in SUPPORTED_CHARACTER_IMAGE_PROTOCOLS:
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


def _openai_image_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    if base.endswith("/v1"):
        return f"{base}/images/generations"
    return f"{base}/v1/images/generations"


def _anthropic_messages_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/messages"):
        return base
    if base.endswith("/v1"):
        return f"{base}/messages"
    return f"{base}/v1/messages"


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


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型未返回合法 JSON 对象")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"模型返回 JSON 解析失败: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("模型返回结果不是 JSON object")
    return payload


def _extract_provider_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "").strip()
            if message:
                return message
        message = str(payload.get("message") or "").strip()
        if message:
            return message
    if response.status_code == 429:
        return "生图助手请求被限流或额度不足，请稍后重试并检查配额"
    return f"上游接口请求失败: HTTP {response.status_code}"


def _raise_for_provider_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(_extract_provider_error_message(response)) from exc


def _build_image_prompt(
    *,
    character_name: str,
    character_description: str,
    story_summary: str | None,
    story_setting: str | None,
    visual_style_name: str | None,
    visual_style_prompt: str | None,
) -> str:
    parts = [
        f"角色名称：{character_name}",
        f"角色描述：{character_description or '待补充'}",
        f"故事概览：{story_summary or '未指定'}",
        f"时代/背景：{story_setting or '未指定'}",
        f"画面风格：{visual_style_name or '未指定'}",
        f"风格提示词：{visual_style_prompt or '未指定'}",
        "请生成一张适合短视频角色设定的单人角色立绘或半身角色参考图。",
    ]
    return "\n".join(parts)


def _save_temp_preview(storage_service, *, image_bytes: bytes, extension: str, filename_hint: str) -> str:
    safe_extension = extension if extension.startswith(".") else f".{extension}" if extension else ".png"
    stored = storage_service.save_bytes(
        filename=f"{filename_hint}{safe_extension}",
        data=image_bytes,
        category="previews/characters",
    )
    return stored.public_url


def _normalize_openai_image_response(data: dict[str, Any], storage_service, *, filename_hint: str) -> dict[str, Any]:
    images = data.get("data") or []
    if not images:
        raise ValueError("生图助手未返回图片结果")
    image = images[0] if isinstance(images[0], dict) else {}
    preview_url = str(image.get("url") or image.get("preview_image_url") or "").strip()
    normalized_prompt = str(image.get("revised_prompt") or data.get("normalized_prompt") or "").strip()
    if preview_url:
        return {"preview_image_url": preview_url, "normalized_prompt": normalized_prompt}
    b64_json = str(image.get("b64_json") or "").strip()
    if not b64_json:
        raise ValueError("生图助手返回缺少 preview_image_url")
    image_bytes = base64.b64decode(b64_json)
    preview_url = _save_temp_preview(storage_service, image_bytes=image_bytes, extension=".png", filename_hint=filename_hint)
    return {"preview_image_url": preview_url, "normalized_prompt": normalized_prompt}


def _normalize_anthropic_response(data: dict[str, Any], storage_service, *, filename_hint: str) -> dict[str, Any]:
    if data.get("preview_image_url"):
        return {
            "preview_image_url": str(data.get("preview_image_url") or "").strip(),
            "normalized_prompt": str(data.get("normalized_prompt") or "").strip(),
        }
    content = _extract_text_content(data.get("content"))
    if not content:
        raise ValueError("生图助手未返回文本内容")
    payload = _extract_json_payload(content)
    preview_url = str(payload.get("preview_image_url") or payload.get("image_url") or payload.get("url") or "").strip()
    normalized_prompt = str(payload.get("normalized_prompt") or "").strip()
    if preview_url:
        return {"preview_image_url": preview_url, "normalized_prompt": normalized_prompt}
    b64_json = str(payload.get("b64_json") or "").strip()
    if not b64_json:
        raise ValueError("生图助手返回缺少 preview_image_url")
    image_bytes = base64.b64decode(b64_json)
    preview_url = _save_temp_preview(storage_service, image_bytes=image_bytes, extension=".png", filename_hint=filename_hint)
    return {"preview_image_url": preview_url, "normalized_prompt": normalized_prompt}


def generate_character_preview(
    assistant_config: dict[str, Any],
    *,
    storage_service,
    character_name: str,
    character_description: str,
    story_summary: str | None = None,
    story_setting: str | None = None,
    visual_style_name: str | None = None,
    visual_style_prompt: str | None = None,
) -> dict[str, Any]:
    errors = validate_character_image_assistant_config(assistant_config)
    if errors:
        raise ValueError("；".join(errors))
    prompt = _build_image_prompt(
        character_name=character_name,
        character_description=character_description,
        story_summary=story_summary,
        story_setting=story_setting,
        visual_style_name=visual_style_name,
        visual_style_prompt=visual_style_prompt,
    )
    protocol = str(assistant_config.get("protocol") or "openai").strip().lower()
    filename_hint = Path(character_name or "character-preview").stem or "character-preview"
    timeout = httpx.Timeout(120.0, connect=20.0)

    if protocol == "anthropic":
        payload = {
            "model": assistant_config["model"],
            "system": str(assistant_config.get("system_prompt") or "").strip() or DEFAULT_CHARACTER_IMAGE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        }
        headers = {
            "x-api-key": str(assistant_config["api_key"]),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = _anthropic_messages_url(str(assistant_config["base_url"]))
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            _raise_for_provider_status(response)
            data = response.json()
        result = _normalize_anthropic_response(data, storage_service, filename_hint=filename_hint)
        return {**result, "normalized_prompt": result.get("normalized_prompt") or prompt}

    payload = {
        "model": assistant_config["model"],
        "prompt": prompt,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    headers = {
        "Authorization": f"Bearer {assistant_config['api_key']}",
        "Content-Type": "application/json",
    }
    url = _openai_image_url(str(assistant_config["base_url"]))
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        _raise_for_provider_status(response)
        data = response.json()
    result = _normalize_openai_image_response(data, storage_service, filename_hint=filename_hint)
    return {**result, "normalized_prompt": result.get("normalized_prompt") or prompt}


def download_preview_image(preview_image_url: str, *, storage_service) -> tuple[str, bytes]:
    url = str(preview_image_url or "").strip()
    if not url:
        raise ValueError("preview_image_url 不能为空")
    public_base = str(storage_service.public_base_url or "").rstrip("/")
    if public_base and url.startswith(public_base):
        relative = url[len(public_base) :].lstrip("/")
        full_path = storage_service.base_dir / relative
        if not full_path.exists():
            raise ValueError("预览图片不存在")
        return full_path.name, full_path.read_bytes()

    timeout = httpx.Timeout(60.0, connect=15.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        _raise_for_provider_status(response)
        image_bytes = response.content
        if not image_bytes:
            raise ValueError("预览图片为空")
        filename = Path(urlparse(str(response.url)).path).name or Path(urlparse(url).path).name or "character-preview.png"
        if "." not in filename:
            extension = mimetypes.guess_extension(response.headers.get("content-type", "").split(";")[0].strip()) or ".png"
            filename = f"{filename}{extension}"
        return filename, image_bytes
