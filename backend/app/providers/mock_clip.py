from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(map(shlex.quote, cmd))}\n{proc.stdout}")


def build_mock_clip(
    *,
    provider_code: str,
    prompt: str,
    width: int,
    height: int,
    duration_s: float,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(f"{provider_code}:{prompt}".encode("utf-8")).hexdigest()
    color = f"#{digest[:6]}"
    duration = max(1.0, float(duration_s or 4))
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={width}x{height}:d={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    _run(cmd)
    return output_path
