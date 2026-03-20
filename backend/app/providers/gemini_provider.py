from __future__ import annotations

from dataclasses import dataclass
from ..config import get_settings
from .base import RenderContext


@dataclass
class GeminiProvider:
    name: str = "gemini"

    def is_configured(self) -> bool:
        return bool(get_settings().GEMINI_API_KEY)

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement Gemini provider.
        raise NotImplementedError("Gemini provider stub (needs GEMINI_API_KEY + implementation).")
