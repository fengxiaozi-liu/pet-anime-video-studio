from __future__ import annotations

from pydantic import BaseModel, Field


class Scene(BaseModel):
    duration_s: float = Field(..., ge=0.5, le=60)
    prompt: str = ""
    subtitle: str | None = None


class Storyboard(BaseModel):
    template_id: str | None = None
    template_name: str | None = None
    platform: str | None = None
    cover_width: int | None = None
    cover_height: int | None = None
    subtitle_safe_margin: int | None = None

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
    def autogen(prompt: str, duration_s: float = 15.0) -> "Storyboard":
        dur = float(duration_s or 15.0)
        per = dur / 3
        p = (prompt or "").strip()
        scenes = [
            Scene(duration_s=per, prompt=p or "Opening scene"),
            Scene(duration_s=per, prompt=p or "Middle scene"),
            Scene(duration_s=per, prompt=p or "Closing scene"),
        ]
        return Storyboard(duration_s=dur, scenes=scenes)

    def with_defaults(self, prompt: str) -> "Storyboard":
        if not self.scenes:
            return Storyboard.autogen(prompt=prompt, duration_s=self.duration_s)
        total = sum(float(scene.duration_s) for scene in self.scenes)
        if total > 0:
            return self.model_copy(update={"duration_s": total})
        return self

    def apply_template(self, template: dict | None) -> "Storyboard":
        if not template:
            return self
        updates = {
            "template_id": template.get("id"),
            "template_name": template.get("name"),
            "platform": template.get("platform"),
            "width": int(template.get("width", self.width)),
            "height": int(template.get("height", self.height)),
            "duration_s": float(template.get("duration_s", self.duration_s)),
            "cover_width": int(template.get("cover_width", self.width)),
            "cover_height": int(template.get("cover_height", self.height)),
            "subtitle_safe_margin": int(template.get("subtitle_safe_margin", 180)),
        }
        return self.model_copy(update=updates)
