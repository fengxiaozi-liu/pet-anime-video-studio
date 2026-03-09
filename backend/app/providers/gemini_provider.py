from __future__ import annotations

import os
from dataclasses import dataclass

from .base import RenderContext


@dataclass
class GeminiProvider:
    name: str = "gemini"

    def is_configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement Gemini provider.
        raise NotImplementedError("Gemini provider stub (needs GEMINI_API_KEY + implementation).")
