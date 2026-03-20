from __future__ import annotations

from dataclasses import dataclass
from ..config import get_settings
from .base import RenderContext


@dataclass
class DoubaoProvider:
    name: str = "doubao"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.DOUBAO_API_KEY or settings.VOLCENGINE_API_KEY)

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement Doubao/Volcengine provider.
        raise NotImplementedError("Doubao provider stub (needs DOUBAO_API_KEY/VOLCENGINE_API_KEY + implementation).")
