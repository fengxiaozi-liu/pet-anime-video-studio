from __future__ import annotations

from typing import Any

PLATFORM_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "douyin-15",
        "platform": "douyin",
        "name": "抖音 15s 竖屏",
        "duration_s": 15,
        "width": 1080,
        "height": 1920,
        "cover_width": 1080,
        "cover_height": 1920,
        "subtitle_safe_margin": 180,
        "description": "快速出片，适合单一情绪和轻剧情。",
    },
    {
        "id": "douyin-25",
        "platform": "douyin",
        "name": "抖音 25s 竖屏",
        "duration_s": 25,
        "width": 1080,
        "height": 1920,
        "cover_width": 1080,
        "cover_height": 1920,
        "subtitle_safe_margin": 180,
        "description": "适合前后反差、轻转场叙事。",
    },
    {
        "id": "douyin-40",
        "platform": "douyin",
        "name": "抖音 40s 竖屏",
        "duration_s": 40,
        "width": 1080,
        "height": 1920,
        "cover_width": 1080,
        "cover_height": 1920,
        "subtitle_safe_margin": 180,
        "description": "适合完整的小故事或多段剧情。",
    },
    {
        "id": "xiaohongshu-20",
        "platform": "xiaohongshu",
        "name": "小红书 20s 竖屏",
        "duration_s": 20,
        "width": 1080,
        "height": 1920,
        "cover_width": 1242,
        "cover_height": 1660,
        "subtitle_safe_margin": 220,
        "description": "适合治愈系日常，封面信息权重更高。",
    },
    {
        "id": "xiaohongshu-35",
        "platform": "xiaohongshu",
        "name": "小红书 35s 竖屏",
        "duration_s": 35,
        "width": 1080,
        "height": 1920,
        "cover_width": 1242,
        "cover_height": 1660,
        "subtitle_safe_margin": 220,
        "description": "适合带一点剧情推进和情绪铺垫。",
    },
    {
        "id": "xiaohongshu-60",
        "platform": "xiaohongshu",
        "name": "小红书 60s 竖屏",
        "duration_s": 60,
        "width": 1080,
        "height": 1920,
        "cover_width": 1242,
        "cover_height": 1660,
        "subtitle_safe_margin": 220,
        "description": "适合完整故事线、强文案和封面经营。",
    },
]

_TEMPLATE_BY_ID = {item["id"]: item for item in PLATFORM_TEMPLATES}


def list_platform_templates() -> list[dict[str, Any]]:
    return [dict(item) for item in PLATFORM_TEMPLATES]


def get_platform_template(template_id: str | None) -> dict[str, Any] | None:
    if not template_id:
        return None
    item = _TEMPLATE_BY_ID.get(template_id)
    return dict(item) if item else None
