from __future__ import annotations

import base64
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

# T2I Provider 调度器（延迟导入，避免循环依赖）
_t2i_dispatcher: "T2IDispatcher | None" = None

def _get_t2i_dispatcher() -> "T2IDispatcher":
    global _t2i_dispatcher
    if _t2i_dispatcher is None:
        from .providers.t2i.dispatcher import T2IDispatcher
        _t2i_dispatcher = T2IDispatcher()
    return _t2i_dispatcher

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

# T2I Provider 列表（由 T2IDispatcher.supported_codes() 动态获取）
_T2I_SUPPORTED_CODES: list[str] = []


def _get_provider_code(assistant_config: dict[str, Any]) -> str:
    """
    从 assistant_config 中提取 T2I Provider 代码。

    优先级：
    1. assistant_config.provider（显式指定）
    2. 默认 "tongyi"
    """
    provider = assistant_config.get("provider")
    if provider and str(provider).strip():
        return str(provider).strip().lower()
    return "tongyi"


def _is_t2i_mode(assistant_config: dict[str, Any]) -> bool:
    """判断是否使用 T2I Provider 模式（而非直接调用 LLM 出图）。"""
    provider = assistant_config.get("provider")
    # provider 为 null / None / 空字符串 → 走原有 LLM 路径
    if provider is None or (isinstance(provider, str) and not provider.strip()):
        return False
    # provider 显式设置，且为已知 T2I provider code
    global _T2I_SUPPORTED_CODES
    if not _T2I_SUPPORTED_CODES:
        try:
            _T2I_SUPPORTED_CODES = _get_t2i_dispatcher().supported_codes()
        except Exception:
            _T2I_SUPPORTED_CODES = []
    code = str(provider).strip().lower()
    return code in _T2I_SUPPORTED_CODES


def validate_character_image_assistant_config(config: dict[str, Any]) -> list[str]:
    """
    校验 assistant 配置。

    支持两种模式：
    - LLM 模式（默认）：校验 protocol / base_url / api_key / model
    - T2I 模式（type="t2i"）：由 T2IDispatcher.validate_provider_config() 校验
    """
    errors: list[str] = []
    cfg_type = str(config.get("type") or "llm").strip().lower()

    if cfg_type == "t2i":
        # T2I Provider 模式
        provider_code = _get_provider_code(config)
        # 构建 Provider 所需的 config dict（只含 T2I 相关字段）
        provider_config = {
            k: v
            for k, v in config.items()
            if k
            in (
                "api_key",
                "base_url",
                "model",
                "default_image_size",
                "default_style",
                "use_async",
                "poll_interval_seconds",
            )
        }
        try:
            dispatcher = _get_t2i_dispatcher()
            errors.extend(dispatcher.validate_provider_config(provider_code, provider_config))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"T2I Provider 初始化失败: {exc}")
        return errors

    # LLM 模式（默认行为）
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


def _openai_task_url(base_url: str, task_id: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/tasks/{task_id}"
    return f"{base}/v1/tasks/{task_id}"


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


def _extract_candidate_url(payload: Any) -> str:
    if isinstance(payload, str):
        value = payload.strip()
        if value.startswith("http://") or value.startswith("https://") or value.startswith("data:image/"):
            return value
        return ""
    if isinstance(payload, list):
        for item in payload:
            candidate = _extract_candidate_url(item)
            if candidate:
                return candidate
        return ""
    if not isinstance(payload, dict):
        return ""

    for key in ("preview_image_url", "image_url", "url"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value

    for key in ("result", "image", "data", "output", "outputs"):
        if key in payload:
            candidate = _extract_candidate_url(payload.get(key))
            if candidate:
                return candidate
    return ""


def _extract_base64_payload(payload: Any) -> str:
    if isinstance(payload, str):
        value = payload.strip()
        if value.startswith("data:image/"):
            marker = value.find("base64,")
            return value[marker + 7 :] if marker >= 0 else ""
        compact = value.replace("\n", "").replace("\r", "")
        if len(compact) > 128 and re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
            return compact
        return ""
    if isinstance(payload, list):
        for item in payload:
            candidate = _extract_base64_payload(item)
            if candidate:
                return candidate
        return ""
    if not isinstance(payload, dict):
        return ""

    for key in ("b64_json", "base64", "image_base64", "image_b64", "image_data"):
        value = _extract_base64_payload(payload.get(key))
        if value:
            return value

    for key in ("result", "image", "data", "output", "outputs"):
        if key in payload:
            candidate = _extract_base64_payload(payload.get(key))
            if candidate:
                return candidate
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


def _raise_payload_error(payload: dict[str, Any]) -> None:
    message = str(
        payload.get("message")
        or payload.get("error")
        or payload.get("detail")
        or ""
    ).strip()
    code = str(payload.get("code") or "").strip()
    if message:
        prefix = f"[{code}] " if code else ""
        raise ValueError(f"生图助手未返回图片结果：{prefix}{message}")


def _raise_missing_image_with_prompt(normalized_prompt: str) -> None:
    if str(normalized_prompt or "").strip():
        raise ValueError("当前生图模型只返回了提示词，没有真正生成图片，请更换支持出图的模型或接口。")


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
            code = str(error.get("code") or "").strip()
            if code:
                return code
        message = str(payload.get("message") or "").strip()
        if message:
            return message
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if isinstance(detail, dict):
            detail_message = str(detail.get("message") or detail.get("msg") or "").strip()
            if detail_message:
                return detail_message
        code = str(payload.get("code") or "").strip()
        if code:
            return code
    if response.status_code == 429:
        return "生图助手请求被限流或额度不足，请稍后重试并检查配额"
    text = response.text.strip()
    if text:
        return f"上游接口请求失败: HTTP {response.status_code} - {text[:400]}"
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


def _cache_preview_url(storage_service, *, preview_url: str, filename_hint: str) -> str:
    source_url = str(preview_url or "").strip()
    if not source_url:
        raise ValueError("preview_image_url 不能为空")
    filename, image_bytes = download_preview_image(source_url, storage_service=storage_service)
    extension = Path(filename).suffix or ".png"
    return _save_temp_preview(
        storage_service,
        image_bytes=image_bytes,
        extension=extension,
        filename_hint=filename_hint,
    )


def _normalize_openai_image_response(data: dict[str, Any], storage_service, *, filename_hint: str) -> dict[str, Any]:
    _raise_payload_error(data)
    images = data.get("data") or data.get("output") or data.get("outputs") or []
    image = images[0] if isinstance(images, list) and images else (images if isinstance(images, dict) else {})
    normalized_prompt = str(
        (image if isinstance(image, dict) else {}).get("revised_prompt")
        or data.get("normalized_prompt")
        or data.get("revised_prompt")
        or ""
    ).strip()
    preview_url = _extract_candidate_url(image or data)
    if preview_url:
        return {
            "preview_image_url": _cache_preview_url(storage_service, preview_url=preview_url, filename_hint=filename_hint),
            "normalized_prompt": normalized_prompt,
        }
    b64_json = _extract_base64_payload(image or data)
    if not b64_json:
        choices = data.get("choices") or []
        if choices:
            message = (choices[0] or {}).get("message") or {}
            content = _extract_text_content(message.get("content"))
            if content:
                try:
                    payload = _extract_json_payload(content)
                except Exception:
                    payload = {"preview_image_url": _extract_candidate_url(content), "b64_json": _extract_base64_payload(content)}
                if isinstance(payload, dict):
                    _raise_payload_error(payload)
                preview_url = _extract_candidate_url(payload)
                if preview_url:
                    return {
                        "preview_image_url": _cache_preview_url(storage_service, preview_url=preview_url, filename_hint=filename_hint),
                        "normalized_prompt": str(payload.get("normalized_prompt") or normalized_prompt or "").strip(),
                    }
                b64_json = _extract_base64_payload(payload)
        if not b64_json:
            _raise_missing_image_with_prompt(normalized_prompt)
            raise ValueError("生图助手返回缺少可识别的图片字段")
    image_bytes = base64.b64decode(b64_json)
    preview_url = _save_temp_preview(storage_service, image_bytes=image_bytes, extension=".png", filename_hint=filename_hint)
    return {"preview_image_url": preview_url, "normalized_prompt": normalized_prompt}


def _is_modelscope_openai_compatible(base_url: str) -> bool:
    host = (urlparse(str(base_url or "")).netloc or "").lower()
    return "modelscope.cn" in host


def _poll_modelscope_task(
    client: httpx.Client,
    *,
    base_url: str,
    api_key: str,
    task_id: str,
    filename_hint: str,
    storage_service,
    normalized_prompt: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-ModelScope-Task-Type": "image_generation",
    }
    url = _openai_task_url(base_url, task_id)
    deadline = time.monotonic() + 180.0
    last_payload: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = client.get(url, headers=headers)
        _raise_for_provider_status(response)
        data = response.json()
        if isinstance(data, dict):
            last_payload = data
        status = str((data or {}).get("task_status") or "").upper()
        if status == "SUCCEED":
            preview_url = _extract_candidate_url(data.get("output_images") or data)
            if not preview_url:
                _raise_payload_error(data)
                raise ValueError("生图助手任务已完成，但未返回 output_images")
            return {
                "preview_image_url": _cache_preview_url(
                    storage_service,
                    preview_url=preview_url,
                    filename_hint=filename_hint,
                ),
                "normalized_prompt": normalized_prompt,
            }
        if status == "FAILED":
            _raise_payload_error(data)
            raise ValueError("生图助手任务执行失败")
        time.sleep(2.0)
    if last_payload:
        _raise_payload_error(last_payload)
    raise ValueError("生图助手任务轮询超时，请稍后重试")


def _normalize_anthropic_response(data: dict[str, Any], storage_service, *, filename_hint: str) -> dict[str, Any]:
    _raise_payload_error(data)
    if _extract_candidate_url(data):
        return {
            "preview_image_url": _cache_preview_url(storage_service, preview_url=_extract_candidate_url(data), filename_hint=filename_hint),
            "normalized_prompt": str(data.get("normalized_prompt") or "").strip(),
        }
    content = _extract_text_content(data.get("content"))
    if not content:
        raise ValueError("生图助手未返回文本内容")
    payload = _extract_json_payload(content)
    _raise_payload_error(payload)
    preview_url = _extract_candidate_url(payload)
    normalized_prompt = str(payload.get("normalized_prompt") or "").strip()
    if preview_url:
        return {
            "preview_image_url": _cache_preview_url(storage_service, preview_url=preview_url, filename_hint=filename_hint),
            "normalized_prompt": normalized_prompt,
        }
    b64_json = _extract_base64_payload(payload)
    if not b64_json:
        _raise_missing_image_with_prompt(normalized_prompt)
        raise ValueError("生图助手返回缺少可识别的图片字段")
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
    filename_hint = Path(character_name or "character-preview").stem or "character-preview"

    # ---------------------------------------------------------------
    # T2I Provider 模式（通过 T2IDispatcher 调度）
    # ---------------------------------------------------------------
    if _is_t2i_mode(assistant_config):
        provider_code = _get_provider_code(assistant_config)
        # 从 assistant_config 提取 Provider 所需的配置字典
        provider_config = {
            k: v
            for k, v in assistant_config.items()
            if k
            in (
                "api_key",
                "base_url",
                "model",
                "default_image_size",
                "default_style",
                "use_async",
                "poll_interval_seconds",
            )
        }
        # 提取风格参数（visual_style_name → style）
        style: str | None = None
        if visual_style_name:
            style = visual_style_name
        elif assistant_config.get("default_style"):
            style = str(assistant_config["default_style"])

        try:
            dispatcher = _get_t2i_dispatcher()
            t2i_result = dispatcher.generate(
                provider_code=provider_code,
                prompt=prompt,
                config=provider_config,
                negative_prompt=None,
                style=style,
                image_size=assistant_config.get("default_image_size"),
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"T2I Provider [{provider_code}] 出图失败: {exc}"
            ) from exc

        if t2i_result.normalized_status == "failed":
            raise ValueError(
                f"T2I Provider [{provider_code}] 出图失败: "
                f"{t2i_result.raw_response}"
            )

        # 将 T2IResult 转换为原有函数返回值格式
        if t2i_result.image_url:
            cached_url = _cache_preview_url(
                storage_service,
                preview_url=t2i_result.image_url,
                filename_hint=filename_hint,
            )
            return {
                "preview_image_url": cached_url,
                "normalized_prompt": t2i_result.normalized_prompt or prompt,
            }
        if t2i_result.image_b64:
            image_bytes = base64.b64decode(t2i_result.image_b64)
            saved_url = _save_temp_preview(
                storage_service,
                image_bytes=image_bytes,
                extension=".png",
                filename_hint=filename_hint,
            )
            return {
                "preview_image_url": saved_url,
                "normalized_prompt": t2i_result.normalized_prompt or prompt,
            }
        raise ValueError(
            f"T2I Provider [{provider_code}] 返回结果缺少图片数据: "
            f"{t2i_result.raw_response}"
        )

    # ---------------------------------------------------------------
    # LLM 模式（原有直接调用 OpenAI/Anthropic API 的逻辑）
    # ---------------------------------------------------------------
    protocol = str(assistant_config.get("protocol") or "openai").strip().lower()
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
    }
    headers = {
        "Authorization": f"Bearer {assistant_config['api_key']}",
        "Content-Type": "application/json",
    }
    if _is_modelscope_openai_compatible(str(assistant_config["base_url"])):
        headers["X-ModelScope-Async-Mode"] = "true"
    else:
        payload["response_format"] = "b64_json"
    url = _openai_image_url(str(assistant_config["base_url"]))
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        _raise_for_provider_status(response)
        data = response.json()
        task_id = str((data or {}).get("task_id") or "").strip()
        if task_id:
            result = _poll_modelscope_task(
                client,
                base_url=str(assistant_config["base_url"]),
                api_key=str(assistant_config["api_key"]),
                task_id=task_id,
                filename_hint=filename_hint,
                storage_service=storage_service,
                normalized_prompt=prompt,
            )
            return {**result, "normalized_prompt": result.get("normalized_prompt") or prompt}
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
