from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Scene(BaseModel):
    duration_s: float = Field(..., ge=0.5, le=60)
    prompt: str = ""
    subtitle: str | None = None


class Storyboard(BaseModel):
    fps: int = Field(30, ge=12, le=60)
    width: int = Field(1280, ge=320, le=3840)
    height: int = Field(720, ge=240, le=2160)
    duration_s: float = Field(15.0, ge=1, le=120)

    style: str = (
        "warm hand-drawn anime, watercolor backgrounds, soft line art, "
        "cozy storybook vibe, gentle lighting"
    )

    # output extras
    subtitles: bool = True
    bgm_volume: float = Field(0.25, ge=0.0, le=2.0)

    # encoding knobs (local backend)
    x264_preset: str = "veryfast"  # ultrafast/superfast/veryfast/faster/fast/medium/slow
    x264_crf: int = Field(26, ge=16, le=34)
    x264_tune: str = "stillimage"

    # debugging
    keep_tmp: bool = False

    scenes: list[Scene] = Field(default_factory=list)

    @staticmethod
    def autogen(prompt: str) -> "Storyboard":
        # simple: 3 scenes, equal split
        dur = 15.0
        per = dur / 3
        p = (prompt or "").strip()
        scenes = [
            Scene(duration_s=per, prompt=p or "Opening scene"),
            Scene(duration_s=per, prompt=p or "Middle scene"),
            Scene(duration_s=per, prompt=p or "Closing scene"),
        ]
        return Storyboard(duration_s=dur, scenes=scenes)

    def with_defaults(self, prompt: str) -> "Storyboard":
        # ensure scenes exist and total duration approx matches
        if not self.scenes:
            return Storyboard.autogen(prompt=prompt)
        return self
