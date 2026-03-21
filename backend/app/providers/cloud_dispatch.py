from __future__ import annotations

from typing import Any

from .base import BaseProvider
from .custom_model_provider import CustomModelProvider, is_custom_provider_code
from .jimeng_provider import JimengProvider


_PROVIDERS: dict[str, BaseProvider] = {
    "jimeng": JimengProvider(),
}
_CUSTOM_PROVIDER = CustomModelProvider()


def get_provider(provider_code: str) -> BaseProvider:
    provider = _PROVIDERS.get(provider_code)
    if provider is None and is_custom_provider_code(provider_code):
        return _CUSTOM_PROVIDER
    if provider is None:
        raise ValueError(f"Unknown provider: {provider_code}. Supported: {sorted(_PROVIDERS.keys())}")
    return provider


def list_registered_providers() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for order, provider_code in enumerate(["jimeng"], start=1):
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
