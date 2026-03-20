from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.providers.local_provider import render_local  # noqa: E402


def make_image(path: Path, text: str, color: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (1280, 720), color=color)
    draw = ImageDraw.Draw(img)
    draw.text((60, 60), text, fill=(255, 255, 255))
    img.save(path)


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def assert_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(
            f"{label}: expected about {expected:.2f}s, got {actual:.2f}s (tolerance ±{tolerance:.2f}s)"
        )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "tmp_test_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        images = [tmp / "img1.png", tmp / "img2.png", tmp / "img3.png"]
        make_image(images[0], "Scene 1", (50, 80, 140))
        make_image(images[1], "Scene 2", (120, 60, 90))
        make_image(images[2], "Scene 3", (60, 120, 80))

        cases = [
            {
                "name": "single_scene_5s",
                "storyboard": {
                    "fps": 30,
                    "width": 1280,
                    "height": 720,
                    "subtitles": False,
                    "scenes": [{"duration_s": 5, "prompt": "single"}],
                },
                "expected_duration": 5.0,
                "tolerance": 0.25,
            },
            {
                "name": "three_scene_15s",
                "storyboard": {
                    "fps": 30,
                    "width": 1280,
                    "height": 720,
                    "subtitles": False,
                    "scenes": [
                        {"duration_s": 5, "prompt": "a"},
                        {"duration_s": 5, "prompt": "b"},
                        {"duration_s": 5, "prompt": "c"},
                    ],
                },
                "expected_duration": 13.8,
                "tolerance": 0.35,
            },
        ]

        results: list[dict[str, float | str]] = []
        for case in cases:
            out_path = output_dir / f"{case['name']}.mp4"
            render_local(
                prompt="duration validation",
                storyboard=case["storyboard"],
                image_paths=images,
                out_path=out_path,
                bgm_path=None,
            )
            duration = probe_duration(out_path)
            assert_close(duration, float(case["expected_duration"]), float(case["tolerance"]), case["name"])
            results.append({"name": case["name"], "duration": round(duration, 3)})

    print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
