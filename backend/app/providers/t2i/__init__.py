"""
pet-anime-video T2I Provider 子系统

TextToImageProvider 父子类架构
------------------------------
Parent: TextToImageProvider (ABC)      → providers/t2i/base_t2i.py
Children:
  - JimengT2IProvider            即梦
  - TongyiWanxiangT2IProvider     通义万相
  - DallET2IProvider              OpenAI DALL-E
  - StableDiffusionT2IProvider    Stable Diffusion
  - T2IDispatcher                 调度器

导出
----
from .base_t2i import TextToImageProvider, T2IResult, T2ITaskSubmission, T2IProviderField
"""

from __future__ import annotations

from .base_t2i import TextToImageProvider

__all__ = [
    "TextToImageProvider",
    "T2IResult",
    "T2ITaskSubmission",
    "T2IProviderField",
]
