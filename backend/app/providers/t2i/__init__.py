"""
pet-anime-video T2I Provider 子系统

TextToImageProvider 父子类架构
------------------------------
Parent: TextToImageProvider (ABC)      → providers/t2i/base_t2i.py
Children:
  - JimengT2IProvider            即梦
  - TongyiWanxiangT2IProvider   通义万相
  - DallET2IProvider             OpenAI DALL-E
  - StableDiffusionT2IProvider   Stable Diffusion

导出
----
from .base_t2i import TextToImageProvider, T2IResult, T2ITaskSubmission, T2IProviderField
from .tongyi_t2i import TongyiWanxiangT2IProvider
"""

from __future__ import annotations

from .base_t2i import TextToImageProvider, T2IResult, T2ITaskSubmission, T2IProviderField
from .tongyi_t2i import TongyiWanxiangT2IProvider
from .dalle_t2i import DallET2IProvider

__all__ = [
    "TextToImageProvider",
    "T2IResult",
    "T2ITaskSubmission",
    "T2IProviderField",
    "TongyiWanxiangT2IProvider",
    "DallET2IProvider",
]
