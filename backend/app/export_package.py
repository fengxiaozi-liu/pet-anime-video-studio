"""
Export Package Generator — M3 milestone.

Produces the deliverable zip containing:
  video.mp4   (already rendered, we copy/serve it)
  cover.png   (FFmpeg first-frame extraction at template cover dimensions)
  title.txt   (single-line title from job prompt)
  caption.txt (generated caption text, up to 150 chars)
  hashtags.txt (platform-aware hashtags list)
  project.json (job metadata + template params for re-use)
"""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from .platform_templates import get_platform_template


# ---------------------------------------------------------------------------
# Caption / hashtag generation (rule-based, no API needed)
# ---------------------------------------------------------------------------

_PLATFORM_KEYWORDS = {
    "douyin": [
        "#宠物", "#萌宠", "#抖音萌宠", "#可爱宠物", "#家有萌宠",
        "#宠物日常", "#猫咪", "#狗狗", "#治愈系", "#每日吸宠",
    ],
    "xiaohongshu": [
        "#宠物", "#萌宠", "#小红书萌宠", "#家有萌宠", "#宠物日记",
        "#治愈系宠物", "#吸猫", "#铲屎官", "#宠物博主", "#可爱汪汪",
    ],
}


def _sanitize(text: str) -> str:
    """Strip control chars, collapse whitespace."""
    return " ".join(text.split())[:200]


def _generate_title(prompt: str, platform: str | None, template_name: str | None) -> str:
    """Derive a single-line title from available context."""
    if template_name:
        return _sanitize(template_name)
    if prompt:
        words = prompt.split()[:8]
        title = " ".join(words)
        return _sanitize(title)
    platform_label = {"douyin": "抖音", "xiaohongshu": "小红书"}.get(platform or "", "宠物")
    return f"{platform_label}宠物可爱瞬间"


def _generate_caption(prompt: str, platform: str | None) -> str:
    """Generate a short caption (≤150 chars) suitable for the platform."""
    base = _sanitize(prompt) if prompt else ""
    emoji = {"douyin": "✨🐾", "xiaohongshu": "🌿🐾"}.get(platform or "", "✨")
    if len(base) <= 120:
        caption = f"{base} {emoji}"
    else:
        caption = f"{base[:117]}... {emoji}"
    return caption[:150]


def _get_hashtags(platform: str | None, count: int = 10) -> list[str]:
    pool = _PLATFORM_KEYWORDS.get(platform or "douyin", _PLATFORM_KEYWORDS["douyin"])
    return pool[:count]


# ---------------------------------------------------------------------------
# Cover image extraction via FFmpeg
# ---------------------------------------------------------------------------

def _extract_cover(video_path: Path, cover_width: int, cover_height: int) -> Path | None:
    """
    Extract the first frame from `video_path` and resize to cover dimensions.
    Returns the path to the extracted PNG, or None on failure.
    """
    cover_path = video_path.with_suffix(".cover.png")
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0.1",           # skip a tiny bit so we land on a real frame
        "-i", str(video_path),
        "-vframes", "1",
        "-vf", f"scale={cover_width}:{cover_height}:force_original_aspect_ratio=decrease,pad={cover_width}:{cover_height}:(ow-iw)/2:(oh-ih)/2:black",
        "-q:v", "2",
        str(cover_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0 and cover_path.exists():
            return cover_path
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Project.json helpers
# ---------------------------------------------------------------------------

def _build_project_json(job: dict) -> dict:
    """Serialize job + resolved template into a re-usable project.json dict."""
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


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def generate_export_package(job_id: str, render_repo, output_dir: Path) -> Path | None:
    """
    Produce an export ZIP at `output_dir` / `{job_id}_export.zip`.
    Returns the zip path, or None if the job is not done / video missing.
    """
    job_obj = render_repo.get(job_id)
    if not job_obj:
        return None
    job = {
        "job_id": job_obj.job_id,
        "status": job_obj.status,
        "output": job_obj.output_path,
        "template_id": job_obj.template_id,
        "template_name": job_obj.template_name,
        "prompt": job_obj.prompt,
        "platform": job_obj.platform,
        "backend": job_obj.backend,
        "provider": job_obj.provider_code,
        "storyboard": job_obj.storyboard,
        "images": job_obj.images,
        "bgm": job_obj.bgm_path,
        "created_at": job_obj.created_at,
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

    # Extract cover (best-effort)
    cover_path = _extract_cover(video_path, cover_w, cover_h)

    # Generate text assets
    title = _generate_title(job.get("prompt", ""), job.get("platform"), job.get("template_name"))
    caption = _generate_caption(job.get("prompt", ""), job.get("platform"))
    hashtags = _get_hashtags(job.get("platform"), count=10)
    project_json = _build_project_json(job)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. video.mp4
        zf.write(video_path, arcname="video.mp4")

        # 2. cover.png (best-effort)
        if cover_path and cover_path.exists():
            zf.write(cover_path, arcname="cover.png")
        else:
            zf.writestr("cover.png", b"", compress_type=zipfile.ZIP_STORED)

        # 3. title.txt
        zf.writestr("title.txt", title.encode("utf-8"))

        # 4. caption.txt
        zf.writestr("caption.txt", caption.encode("utf-8"))

        # 5. hashtags.txt
        zf.writestr("hashtags.txt", ("\n".join(hashtags)).encode("utf-8"))

        # 6. project.json
        zf.writestr(
            "project.json",
            json.dumps(project_json, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    return zip_path
