from __future__ import annotations

import os
from dataclasses import dataclass

from .base import RenderContext


@dataclass
class DoubaoProvider:
    name: str = "doubao"

    def is_configured(self) -> bool:
        # Common patterns: DOUBAO_API_KEY or VOLCENGINE_API_KEY
        return bool(os.getenv("DOUBAO_API_KEY") or os.getenv("VOLCENGINE_API_KEY"))

    def render(self, ctx: RenderContext) -> None:
        # TODO: Implement Doubao/Volcengine provider.
        raise NotImplementedError("Doubao provider stub (needs DOUBAO_API_KEY/VOLCENGINE_API_KEY + implementation).")
