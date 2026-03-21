from __future__ import annotations

import math
import shlex
import subprocess
import shutil
from pathlib import Path
from typing import Any

import httpx

def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(shlex.quote, cmd))}\n{p.stdout}")


def _escape_ffmpeg_path(p: Path) -> str:
    # For ffmpeg filter args (e.g. subtitles=...), ':' is a separator.
    # Escaping is conservative to avoid breaking common Linux paths.
    s = str(p)
    s = s.replace("\\", "\\\\")
    s = s.replace(":", "\\:")
    s = s.replace("'", "\\'")
    return s


def _sec_to_ts(sec: float) -> str:
    # SRT timestamp: HH:MM:SS,mmm
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(*, storyboard: dict[str, Any], srt_path: Path) -> None:
    scenes = storyboard.get("scenes") or []
    lines: list[str] = []
    t = 0.0
    idx = 1
    for scene in scenes:
        dur = float(scene.get("duration_s", 0))
        if dur <= 0:
            continue
        text = (scene.get("subtitle") or scene.get("prompt") or "").strip()
        if not text:
            t += dur
            continue
        start = _sec_to_ts(t)
        end = _sec_to_ts(t + dur)
        lines += [str(idx), f"{start} --> {end}", text, ""]
        idx += 1
        t += dur

    srt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _finalize(
    *,
    base_video: Path,
    storyboard: dict[str, Any],
    out_path: Path,
    bgm_path: Path | None,
    tmp_dir: Path,
) -> None:
    """Apply subtitles + BGM to the base video."""

    current = base_video

    # 1) subtitles
    if bool(storyboard.get("subtitles", True)):
        srt = tmp_dir / "subtitles.srt"
        _write_srt(storyboard=storyboard, srt_path=srt)
        if srt.exists() and srt.stat().st_size > 0:
            subbed = tmp_dir / "subbed.mp4"
            # libass style
            force_style = "Fontsize=28,Outline=2,Shadow=0,Alignment=2,MarginV=30"
            vf = f"subtitles={_escape_ffmpeg_path(srt)}:force_style='{force_style}'"

            preset = storyboard.get("x264_preset", "medium")
            crf = str(storyboard.get("x264_crf", 20))
            tune = storyboard.get("x264_tune", "stillimage")

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(current),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                str(preset),
                "-crf",
                crf,
                "-tune",
                str(tune),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                str(subbed),
            ]
            _run(cmd)
            current = subbed

    # 2) bgm
    if bgm_path is not None:
        if not bgm_path.exists():
            raise FileNotFoundError(f"BGM not found: {bgm_path}")

        vol = float(storyboard.get("bgm_volume", 0.25))
        final = out_path
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(current),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm_path),
            "-shortest",
            "-filter:a",
            f"volume={vol}",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(final),
        ]
        _run(cmd)
    else:
        # ensure output exists at out_path
        if current != out_path:
            if out_path.exists():
                out_path.unlink()
            current.replace(out_path)
def render_local(
    *,
    prompt: str,
    storyboard: dict[str, Any],
    image_paths: list[Path],
    out_path: Path,
    bgm_path: Path | None = None,
) -> None:
    """Local video render.

    Strategy:
    - Create one segment per scene using FFmpeg `zoompan` for gentle camera motion.
    - Crossfade segments.
    - Optionally burn subtitles (SRT) and add BGM.

    This is intentionally model-free so it runs on WSL with good perceived quality.
    """

    fps = int(storyboard.get("fps", 30))
    width = int(storyboard.get("width", 1280))
    height = int(storyboard.get("height", 720))
    scenes = storyboard.get("scenes") or []
    if not scenes:
        raise ValueError("Storyboard scenes missing")

    # map scenes to images in a round-robin way
    if not image_paths:
        raise ValueError("No images")

    tmp_dir = out_path.parent / (out_path.stem + "_tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    seg_paths: list[Path] = []
    for i, scene in enumerate(scenes):
        dur = float(scene.get("duration_s", 5))
        img = image_paths[i % len(image_paths)]
        seg = tmp_dir / f"seg_{i:02d}.mp4"

        frames = max(1, int(math.ceil(dur * fps)))

        # zoompan: subtle zoom in
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(1.10,zoom+0.0008)':d={frames}:s={width}x{height}:fps={fps},"
            f"format=yuv420p"
        )

        preset = storyboard.get("x264_preset", "medium")
        crf = str(storyboard.get("x264_crf", 20))
        tune = storyboard.get("x264_tune", "stillimage")

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(img),
            "-vf",
            vf,
            "-frames:v",
            str(frames),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            str(preset),
            "-crf",
            crf,
            "-tune",
            str(tune),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(seg),
        ]
        _run(cmd)
        seg_paths.append(seg)

    base_video = tmp_dir / "base.mp4"

    if len(seg_paths) == 1:
        # if only one segment, just use it as base
        if base_video.exists():
            base_video.unlink()
        seg_paths[0].replace(base_video)
        _finalize(
            base_video=base_video,
            storyboard=storyboard,
            out_path=out_path,
            bgm_path=bgm_path,
            tmp_dir=tmp_dir,
        )

        if not bool(storyboard.get("keep_tmp", False)):
            try:
                for p in sorted(tmp_dir.glob("**/*"), reverse=True):
                    if p.is_file():
                        p.unlink(missing_ok=True)
                    elif p.is_dir():
                        p.rmdir()
                tmp_dir.rmdir()
            except Exception:
                pass

        return

    # Build xfade chain.
    # We use a constant fade duration.
    fade = 0.6

    # input args
    cmd = ["ffmpeg", "-y"]
    for p in seg_paths:
        cmd += ["-i", str(p)]

    # filter graph
    # xfade offset is cumulative duration minus fade.
    offsets = []
    t = float(scenes[0].get("duration_s", 5))
    for i in range(1, len(seg_paths)):
        offsets.append(max(0.0, t - fade))
        t += float(scenes[i].get("duration_s", 5)) - fade

    fg = []
    last = "[0:v]"
    for i in range(1, len(seg_paths)):
        out = f"[v{i}]"
        off = offsets[i - 1]
        fg.append(f"{last}[{i}:v]xfade=transition=fade:duration={fade}:offset={off}{out}")
        last = out

    filter_complex = ";".join(fg)

    preset = storyboard.get("x264_preset", "medium")
    crf = str(storyboard.get("x264_crf", 20))
    tune = storyboard.get("x264_tune", "stillimage")

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        last,
        "-c:v",
        "libx264",
        "-preset",
        str(preset),
        "-crf",
        crf,
        "-tune",
        str(tune),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(base_video),
    ]

    _run(cmd)

    _finalize(
        base_video=base_video,
        storyboard=storyboard,
        out_path=out_path,
        bgm_path=bgm_path,
        tmp_dir=tmp_dir,
    )

    # cleanup tmp unless explicitly kept (helps avoid disk bloat)
    if not bool(storyboard.get("keep_tmp", False)):
        try:
            for p in sorted(tmp_dir.glob("**/*"), reverse=True):
                if p.is_file():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    p.rmdir()
            tmp_dir.rmdir()
        except Exception:
            # best-effort cleanup only
            pass


def _download_scene_clip(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("file://"):
        source = Path(url[7:])
        shutil.copy2(source, target)
        return target
    if url.startswith("/") and Path(url).exists():
        shutil.copy2(Path(url), target)
        return target
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with target.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
    return target


def compose_remote_clips(
    *,
    storyboard: dict[str, Any],
    scene_video_urls: list[str],
    out_path: Path,
    bgm_path: Path | None = None,
) -> Path:
    if not scene_video_urls:
        raise ValueError("No scene video URLs to compose")

    tmp_dir = out_path.parent / f"{out_path.stem}_compose_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for index, url in enumerate(scene_video_urls):
        clip_path = tmp_dir / f"scene_{index:02d}.mp4"
        downloaded.append(_download_scene_clip(url, clip_path))

    if len(downloaded) == 1:
        base_video = tmp_dir / "base.mp4"
        shutil.copy2(downloaded[0], base_video)
    else:
        concat_file = tmp_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{clip.resolve()}'" for clip in downloaded),
            encoding="utf-8",
        )
        base_video = tmp_dir / "base.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(base_video),
        ]
        _run(cmd)

    _finalize(
        base_video=base_video,
        storyboard=storyboard,
        out_path=out_path,
        bgm_path=bgm_path,
        tmp_dir=tmp_dir,
    )
    return out_path
