from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class RenderContext:
    provider: str
    prompt: str
    storyboard: dict[str, Any]
    image_paths: list[Path]
    out_path: Path
    bgm_path: Path | None = None


class CloudProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def render(self, ctx: RenderContext) -> None: ...
