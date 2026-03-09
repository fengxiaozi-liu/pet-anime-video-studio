from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import RenderContext
from .doubao_provider import DoubaoProvider
from .gemini_provider import GeminiProvider
from .kling_provider import KlingProvider
from .openai_provider import OpenAIProvider


_PROVIDERS = {
    "kling": KlingProvider(),
    "openai": OpenAIProvider(),
    "gemini": GeminiProvider(),
    "doubao": DoubaoProvider(),
}


def render_cloud(
    *,
    provider: str,
    prompt: str,
    storyboard: dict[str, Any],
    image_paths: list[Path],
    out_path: Path,
    bgm_path: Path | None = None,
) -> None:
    p = _PROVIDERS.get(provider)
    if p is None:
        raise ValueError(f"Unknown provider: {provider}. Supported: {sorted(_PROVIDERS.keys())}")

    ctx = RenderContext(
        provider=provider,
        prompt=prompt,
        storyboard=storyboard,
        image_paths=image_paths,
        out_path=out_path,
        bgm_path=bgm_path,
    )

    if not p.is_configured():
        raise RuntimeError(
            f"Cloud provider '{provider}' is not configured. "
            f"Set its API key/environment variables first, or use backend=local/auto."
        )

    p.render(ctx)
