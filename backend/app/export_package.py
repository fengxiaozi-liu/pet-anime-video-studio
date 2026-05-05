"""Export package generation for rendered video jobs."""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from .platform_templates import get_platform_template


_PLATFORM_KEYWORDS = {
    "douyin": [
        "#短视频", "#AI视频", "#创意视频", "#视频制作", "#分镜脚本",
        "#视觉创作", "#内容创作", "#视频生成", "#创作者工具", "#故事短片",
    ],
    "xiaohongshu": [
        "#短视频创作", "#AI创作", "#视频工具", "#内容灵感", "#视觉表达",
        "#脚本策划", "#分镜设计", "#创作工作流", "#视频生成", "#灵感记录",
    ],
}


def _sanitize(text: str) -> str:
    """Strip control chars and collapse whitespace."""
    return " ".join(text.split())[:200]


def _generate_title(prompt: str, platform: str | None, template_name: str | None) -> str:
    """Derive a single-line title from available context."""
    if template_name:
        return _sanitize(template_name)
    if prompt:
        words = prompt.split()[:8]
        return _sanitize(" ".join(words))
    platform_label = {"douyin": "抖音", "xiaohongshu": "小红书"}.get(platform or "", "通用")
    return f"{platform_label}短视频项目"


def _generate_caption(prompt: str, platform: str | None) -> str:
    """Generate a short caption suitable for the target platform."""
    base = _sanitize(prompt) if prompt else "记录一个新的短视频创意"
    suffix = {"douyin": "一起看看", "xiaohongshu": "灵感存档"}.get(platform or "", "视频创作")
    caption = f"{base} {suffix}"
    if len(caption) > 150:
        caption = f"{base[:140]}..."
    return caption[:150]


def _get_hashtags(platform: str | None, count: int = 10) -> list[str]:
    pool = _PLATFORM_KEYWORDS.get(platform or "douyin", _PLATFORM_KEYWORDS["douyin"])
    return pool[:count]


def _extract_cover(video_path: Path, cover_width: int, cover_height: int) -> Path | None:
    """Extract and resize the first usable video frame."""
    cover_path = video_path.with_suffix(".cover.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "0.1",
        "-i",
        str(video_path),
        "-vframes",
        "1",
        "-vf",
        (
            f"scale={cover_width}:{cover_height}:force_original_aspect_ratio=decrease,"
            f"pad={cover_width}:{cover_height}:(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-q:v",
        "2",
        str(cover_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0 and cover_path.exists():
            return cover_path
    except Exception:
        pass
    return None


def _build_project_json(job: dict) -> dict:
    """Serialize job and resolved template into a reusable project.json dict."""
    template_id = job.get("template_id")
    template = get_platform_template(template_id)
    return {
        "version": "1.0",
        "created_at": job.get("created_at"),
        "job_id": job.get("job_id"),
        "template": template or {},
        "prompt": job.get("prompt", ""),
        "platform": job.get("platform"),
        "backend": job.get("backend"),
        "provider": job.get("provider"),
        "storyboard": job.get("storyboard", {}),
        "images": job.get("images", []),
        "bgm": job.get("bgm"),
    }


def _job_value(job_obj, key: str, default=None):
    if isinstance(job_obj, dict):
        return job_obj.get(key, default)
    return getattr(job_obj, key, default)


def generate_export_package(job_id: str, render_repo, output_dir: Path) -> Path | None:
    """Produce an export ZIP at `output_dir` / `{job_id}_export.zip`."""
    job_obj = render_repo.get(job_id)
    if not job_obj:
        return None
    job = {
        "job_id": _job_value(job_obj, "job_id"),
        "status": _job_value(job_obj, "status"),
        "output": _job_value(job_obj, "output_path", _job_value(job_obj, "output", "")),
        "template_id": _job_value(job_obj, "template_id"),
        "template_name": _job_value(job_obj, "template_name"),
        "prompt": _job_value(job_obj, "prompt", ""),
        "platform": _job_value(job_obj, "platform"),
        "backend": _job_value(job_obj, "backend"),
        "provider": _job_value(job_obj, "provider_code", _job_value(job_obj, "provider")),
        "storyboard": _job_value(job_obj, "storyboard", {}),
        "images": _job_value(job_obj, "images", []),
        "bgm": _job_value(job_obj, "bgm_path", _job_value(job_obj, "bgm")),
        "created_at": _job_value(job_obj, "created_at"),
    }
    if job.get("status") != "done":
        return None

    video_path = Path(job.get("output", ""))
    if not video_path.exists():
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{job_id}_export.zip"

    template = get_platform_template(job.get("template_id"))
    cover_w = template.get("cover_width", 1080) if template else 1080
    cover_h = template.get("cover_height", 1920) if template else 1920

    cover_path = _extract_cover(video_path, cover_w, cover_h)

    title = _generate_title(job.get("prompt", ""), job.get("platform"), job.get("template_name"))
    caption = _generate_caption(job.get("prompt", ""), job.get("platform"))
    hashtags = _get_hashtags(job.get("platform"), count=10)
    project_json = _build_project_json(job)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(video_path, arcname="video.mp4")
        if cover_path and cover_path.exists():
            zf.write(cover_path, arcname="cover.png")
        else:
            zf.writestr("cover.png", b"", compress_type=zipfile.ZIP_STORED)
        zf.writestr("title.txt", title.encode("utf-8"))
        zf.writestr("caption.txt", caption.encode("utf-8"))
        zf.writestr("hashtags.txt", ("\n".join(hashtags)).encode("utf-8"))
        zf.writestr(
            "project.json",
            json.dumps(project_json, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    return zip_path
