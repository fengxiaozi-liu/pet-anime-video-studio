from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseProvider, RenderContext
from .doubao_provider import DoubaoProvider
from .gemini_provider import GeminiProvider
from .jimeng_provider import JimengProvider
from .kling_provider import KlingProvider
from .openai_provider import OpenAIProvider


_PROVIDERS: dict[str, BaseProvider] = {
    "jimeng": JimengProvider(),
    "openai": OpenAIProvider(),
    "kling": KlingProvider(),  # legacy compatibility
    "gemini": GeminiProvider(),  # legacy compatibility
    "doubao": DoubaoProvider(),  # legacy compatibility
}


def get_provider(provider_code: str) -> BaseProvider:
    provider = _PROVIDERS.get(provider_code)
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_code}. Supported: {sorted(_PROVIDERS.keys())}")
    return provider


def list_registered_providers() -> list[dict[str, Any]]:
    public_codes = ["jimeng", "openai"]
    items: list[dict[str, Any]] = []
    for order, provider_code in enumerate(public_codes, start=1):
        provider = _PROVIDERS[provider_code]
        items.append(
            {
                "provider_code": provider.code(),
                "display_name": provider.display_name(),
                "description": provider.description(),
                "capabilities": provider.get_capabilities(),
                "config_fields": [field.to_dict() for field in provider.list_config_fields()],
                "sort_order": order,
            }
        )
    return items


def render_cloud(
    *,
    provider: str,
    prompt: str,
    storyboard: dict[str, Any],
    image_paths: list[Path],
    out_path: Path,
    bgm_path: Path | None = None,
) -> None:
    selected = get_provider(provider)
    legacy_render = getattr(selected, "render", None)
    if callable(legacy_render):
        legacy_render(
            RenderContext(
                provider=provider,
                prompt=prompt,
                storyboard=storyboard,
                image_paths=image_paths,
                out_path=out_path,
                bgm_path=bgm_path,
            )
        )
        return
    raise NotImplementedError(f"Provider '{provider}' no longer supports legacy render_cloud() execution.")
