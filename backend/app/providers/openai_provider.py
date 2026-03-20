from __future__ import annotations

from dataclasses import dataclass
from ..config import get_settings
from .base import RenderContext


@dataclass
class OpenAIProvider:
    name: str = "openai"

    def is_configured(self) -> bool:
        return bool(get_settings().OPENAI_API_KEY)

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement OpenAI video/image pipeline when available/desired.
        raise NotImplementedError("OpenAI provider stub (needs OPENAI_API_KEY + implementation).")
