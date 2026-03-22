"""
图片字段提取工具

支持从多种上游响应格式中提取 image_url / image_b64。
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any


def extract_image_from_response(data: dict[str, Any]) -> dict[str, str]:
    """
    从上游响应字典中提取 image_url 或 image_b64。
    返回 {"image_url": ..., "image_b64": ...}，至少有一个非空则返回。
    """
    # 1. image_url 候选字段（按优先级）
    for key in (
        "image_url",
        "url",
        "output_url",
        "data.url",
        "data[0].url",
        "result.url",
        "images[0]",
        "output.image_url",
        "result.image_url",
    ):
        value = _get_nested(data, key)
        if value and _is_url(str(value)):
            return {"image_url": str(value), "image_b64": ""}

    # 2. b64_json 候选字段
    for key in (
        "b64_json",
        "base64",
        "image_base64",
        "image_b64",
        "data.b64_json",
        "result.b64_json",
    ):
        value = _get_nested(data, key)
        b64 = _normalize_b64(value)
        if b64:
            return {"image_url": "", "image_b64": b64}

    # 3. 递归搜索 list
    if isinstance(data, dict):
        for v in data.values():
            found = _search_in_value(v)
            if found:
                return found

    # 4. 尝试在纯文本中找 data URI
    text = _try_serialize_for_search(data)
    b64_in_text = _extract_b64_from_text(text)
    if b64_in_text:
        return {"image_url": "", "image_b64": b64_in_text}

    return {"image_url": "", "image_b64": ""}


def _get_nested(data: dict[str, Any], key: str) -> Any:
    """支持 '.' 和 '[]' 的嵌套访问，如 'data[0].url'"""
    if not isinstance(data, dict):
        return None
    parts = key.split(".")
    current: Any = data
    for part in parts:
        if "[" in part:
            name, idx_str = _split_bracket(part)
            current = current.get(name) if isinstance(current, dict) else None
            if current is None:
                return None
            try:
                idx = int(idx_str)
                current = current[idx]
            except (ValueError, IndexError, TypeError):
                return None
        else:
            current = current.get(part) if isinstance(current, dict) else None
            if current is None:
                return None
    return current


def _split_bracket(s: str) -> tuple[str, str]:
    """从 'field[0]' 拆出 'field' 和 '0'"""
    name, bracket = s.split("[", 1)
    return name, bracket.rstrip("]")


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://") or value.startswith("data:image/")


def _normalize_b64(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    if text.startswith("data:image/"):
        marker = text.find("base64,")
        return text[marker + 7 :] if marker >= 0 else text
    compact = text.replace("\n", "").replace("\r", "").replace(" ", "")
    if len(compact) > 128 and re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        return compact
    return ""


def _search_in_value(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        return extract_image_from_response(value)
    if isinstance(value, list):
        for item in value:
            found = _search_in_value(item)
            if found and (found["image_url"] or found["image_b64"]):
                return found
    return None


def _try_serialize_for_search(data: Any) -> str:
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)


def _extract_b64_from_text(text: str) -> str:
    """从文本中提取 data:image/...;base64,XXX 格式"""
    m = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", text)
    if m:
        return m.group(1)
    # 宽松匹配：超长 base64 字符串
    matches = re.findall(r"([A-Za-z0-9+/]{200,}={0,2})", text)
    for candidate in matches:
        normalized = _normalize_b64(candidate)
        if normalized:
            return normalized
    return ""
