from __future__ import annotations

import tempfile
from pathlib import Path

import sys

from PIL import Image, ImageDraw

# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.providers.local_provider import render_local  # noqa: E402
from backend.app.schema import Storyboard  # noqa: E402


def make_image(path: Path, text: str, color: tuple[int, int, int]):
    img = Image.new("RGB", (1280, 720), color=color)
    d = ImageDraw.Draw(img)
    d.text((60, 60), text, fill=(255, 255, 255))
    img.save(path)


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / ".data" / "demo.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        imgs = [
            td / "1.png",
            td / "2.png",
            td / "3.png",
        ]
        make_image(imgs[0], "Scene 1", (50, 80, 140))
        make_image(imgs[1], "Scene 2", (120, 60, 90))
        make_image(imgs[2], "Scene 3", (60, 120, 80))

        sb = Storyboard.autogen(prompt="A cute pet adventure").model_dump()
        sb["subtitles"] = True
        sb["bgm_volume"] = 0.25

        render_local(
            prompt="A cute pet adventure",
            storyboard=sb,
            image_paths=imgs,
            out_path=out,
            bgm_path=None,
        )

    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
