from __future__ import annotations

import json
import ssl
import time
from typing import Any
from urllib.parse import urlparse

import httpx


DEFAULT_STORY_ASSISTANT_SYSTEM_PROMPT = """
你是一个中文短视频策划助手。请根据用户给出的主题、风格、角色和画面要求，输出一个可直接用于视频工作台编辑的故事策划结果。

你必须返回严格 JSON，不要输出 Markdown，不要输出解释文字。JSON 结构如下：
{
  "story_summary": "一句到三句的内容概览",
  "story_text": "完整策划正文，必须包含【内容概览】【角色列表】【分镜脚本】三个段落标题",
  "scenes": [
    {
      "title": "分镜标题",
      "prompt": "画面描述",
      "subtitle": "字幕文案",
      "duration_s": 4
    }
  ]
}

要求：
- 默认生成 1 - N 个分镜
- 每个分镜的 duration_s 必须是正数，建议 3 到 6 秒
- story_text 必须与 scenes 内容一致
- 分镜 prompt 要可直接用于图像或视频生成
""".strip()

SUPPORTED_STORY_ASSISTANT_PROTOCOLS = {"openai", "anthropic"}


def validate_story_assistant_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    protocol = str(config.get("protocol") or "openai").strip().lower()
    base_url = str(config.get("base_url") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    model = str(config.get("model") or "").strip()
    if protocol not in SUPPORTED_STORY_ASSISTANT_PROTOCOLS:
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
    temperature = config.get("temperature", 0.7)
    try:
        temp = float(temperature)
    except (TypeError, ValueError):
        errors.append("temperature 必须是数字")
    else:
        if temp < 0 or temp > 2:
            errors.append("temperature 必须在 0 到 2 之间")
    return errors


def _openai_messages_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


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


def _scene_block(scene: dict[str, Any], index: int) -> str:
    title = str(scene.get("title") or f"分镜 {index + 1}").strip()
    prompt = str(scene.get("prompt") or "").strip()
    subtitle = str(scene.get("subtitle") or "").strip()
    lines = [f"分镜{index + 1}：{title}"]
    if prompt:
        lines.append(prompt)
    if subtitle:
        lines.append(f"字幕：{subtitle}")
    return "\n".join(lines)


def _compose_story_text(summary: str, scenes: list[dict[str, Any]], characters: list[dict[str, Any]]) -> str:
    role_lines = []
    for index, item in enumerate(characters, start=1):
        role_lines.append(f"{index}. {item.get('name') or f'角色{index}'}：{item.get('description') or '待补充角色描述'}")
    if not role_lines:
        role_lines.append("1. 暂无角色设定，请后续补充。")
    scene_lines = "\n\n".join(_scene_block(scene, index) for index, scene in enumerate(scenes)) or "待生成分镜脚本。"
    return f"【内容概览】\n{summary}\n\n【角色列表】\n" + "\n".join(role_lines) + f"\n\n【分镜脚本】\n{scene_lines}"


def _normalize_story_response(payload: dict[str, Any], characters: list[dict[str, Any]]) -> dict[str, Any]:
    summary = str(payload.get("story_summary") or "").strip()
    if not summary:
        raise ValueError("模型返回缺少 story_summary")
    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("模型返回缺少 scenes")
    scenes: list[dict[str, Any]] = []
    for index, scene in enumerate(raw_scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"scenes[{index}] 不是对象")
        title = str(scene.get("title") or f"分镜 {index + 1}").strip()
        prompt = str(scene.get("prompt") or "").strip()
        subtitle = str(scene.get("subtitle") or "").strip()
        if not prompt:
            raise ValueError(f"scenes[{index}] 缺少 prompt")
        try:
            duration_s = float(scene.get("duration_s") or 4)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"scenes[{index}] 的 duration_s 非法") from exc
        scenes.append(
            {
                "title": title,
                "prompt": prompt,
                "subtitle": subtitle,
                "duration_s": duration_s if duration_s > 0 else 4.0,
            }
        )
    story_text = str(payload.get("story_text") or "").strip() or _compose_story_text(summary, scenes, characters)
    return {
        "story_summary": summary,
        "story_text": story_text,
        "scenes": scenes,
    }


def _build_user_prompt(
    *,
    prompt: str,
    aspect_ratio: str | None,
    template_name: str | None,
    visual_style_name: str | None,
    visual_style_prompt: str | None,
    characters: list[dict[str, Any]],
) -> str:
    character_lines = [
        f"- {item.get('name') or '未命名角色'}：{item.get('description') or '无描述'}"
        for item in characters
    ] or ["- 暂无已选角色"]
    parts = [
        f"主题需求：{prompt}",
        f"视频比例：{aspect_ratio or '未指定'}",
        f"模板：{template_name or '未指定'}",
        f"画面风格：{visual_style_name or '未指定'}",
        f"风格提示词：{visual_style_prompt or '未指定'}",
        "已选角色：",
        "\n".join(character_lines),
        "请生成适合短视频工作台使用的故事概览、策划正文和分镜草稿。",
    ]
    return "\n".join(parts)


def _extract_provider_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            code = str(error.get("code") or "").strip()
            message = str(error.get("message") or "").strip()
            if code == "insufficient_quota":
                return "故事助手额度不足，请检查 API 项目的 billing / quota 配置"
            if code == "invalid_api_key":
                return "故事助手 API Key 无效，请检查配置"
            if code == "model_not_found":
                return "故事助手模型不存在或当前 key 无权限访问"
            if message:
                return message
        message = str(payload.get("message") or "").strip()
        if message:
            return message
    if response.status_code == 429:
        return "故事助手请求被限流或额度不足，请稍后重试并检查配额"
    return f"上游接口请求失败: HTTP {response.status_code}"


def _raise_for_provider_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(_extract_provider_error_message(response)) from exc


def _is_retryable_transport_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError)):
        return True
    cause = getattr(exc, "__cause__", None)
    if isinstance(cause, ssl.SSLError):
        return True
    message = str(exc).lower()
    return "handshake operation timed out" in message or "ssl" in message and "timed out" in message


def _post_json_with_retry(
    *,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: httpx.Timeout,
    max_attempts: int = 3,
) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                _raise_for_provider_status(response)
                return response.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= max_attempts or not _is_retryable_transport_error(exc):
                break
            time.sleep(1.2 * attempt)
    if last_exc is not None:
        if _is_retryable_transport_error(last_exc):
            raise ValueError("故事助手连接上游超时，请稍后重试或检查当前助手的网络连通性") from last_exc
        raise last_exc
    raise ValueError("故事助手请求失败")


def _generate_via_openai(
    assistant_config: dict[str, Any],
    *,
    system_prompt: str,
    user_prompt: str,
    characters: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "model": assistant_config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(assistant_config.get("temperature") or 0.7),
    }
    headers = {
        "Authorization": f"Bearer {assistant_config['api_key']}",
        "Content-Type": "application/json",
    }
    url = _openai_messages_url(str(assistant_config["base_url"]))
    timeout = httpx.Timeout(90.0, connect=30.0)
    data = _post_json_with_retry(url=url, headers=headers, payload=payload, timeout=timeout)
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("模型未返回 choices")
    message = choices[0].get("message") or {}
    content = _extract_text_content(message.get("content"))
    if not content:
        raise ValueError("模型未返回文本内容")
    return _normalize_story_response(_extract_json_payload(content), characters)


def _generate_via_anthropic(
    assistant_config: dict[str, Any],
    *,
    system_prompt: str,
    user_prompt: str,
    characters: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "model": assistant_config["model"],
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": float(assistant_config.get("temperature") or 0.7),
        "max_tokens": 4000,
    }
    headers = {
        "x-api-key": str(assistant_config["api_key"]),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    url = _anthropic_messages_url(str(assistant_config["base_url"]))
    timeout = httpx.Timeout(90.0, connect=30.0)
    data = _post_json_with_retry(url=url, headers=headers, payload=payload, timeout=timeout)
    content = _extract_text_content(data.get("content"))
    if not content:
        raise ValueError("模型未返回文本内容")
    return _normalize_story_response(_extract_json_payload(content), characters)


def generate_story_draft(
    assistant_config: dict[str, Any],
    *,
    prompt: str,
    aspect_ratio: str | None = None,
    template_name: str | None = None,
    visual_style_name: str | None = None,
    visual_style_prompt: str | None = None,
    characters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors = validate_story_assistant_config(assistant_config)
    if errors:
        raise ValueError("；".join(errors))
    characters = characters or []
    protocol = str(assistant_config.get("protocol") or "openai").strip().lower()
    system_prompt = str(assistant_config.get("system_prompt") or "").strip() or DEFAULT_STORY_ASSISTANT_SYSTEM_PROMPT
    user_prompt = _build_user_prompt(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        template_name=template_name,
        visual_style_name=visual_style_name,
        visual_style_prompt=visual_style_prompt,
        characters=characters,
    )
    if protocol == "anthropic":
        return _generate_via_anthropic(
            assistant_config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            characters=characters,
        )
    return _generate_via_openai(
        assistant_config,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        characters=characters,
    )
