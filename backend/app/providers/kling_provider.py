from __future__ import annotations

from dataclasses import dataclass
from ..config import get_settings
from .base import RenderContext


@dataclass
class KlingProvider:
    name: str = "kling"

    def is_configured(self) -> bool:
        return bool(get_settings().KLING_API_KEY)

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement Kling (可灵) image-to-video or multi-image-to-video API.
        # Recommended: submit job -> poll -> download -> postprocess (BGM/subtitles).
        # Keep endpoints configurable:
        #   KLING_BASE_URL
        #   KLING_CREATE_ENDPOINT
        #   KLING_POLL_ENDPOINT
        #   KLING_RESULT_FIELD / etc
        raise NotImplementedError(
            "Kling provider stub. Set KLING_API_KEY and implement endpoints in kling_provider.py."
        )
