from __future__ import annotations

import os
from dataclasses import dataclass

from .base import RenderContext


@dataclass
class OpenAIProvider:
    name: str = "openai"

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement OpenAI video/image pipeline when available/desired.
        raise NotImplementedError("OpenAI provider stub (needs OPENAI_API_KEY + implementation).")
