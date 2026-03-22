"""
T2IDispatcher - T2I Provider 统一调度器

职责：
1. 根据 provider_code 路由到对应 Provider
2. 统一暴露 generate / submit / poll 接口
3. 提供 Provider 元信息查询能力

调用链：
  generate()  → Provider.generate()
  submit()    → Provider.submit()
  poll()      → Provider.poll()
  list_providers() → 各 Provider 的 metadata
"""

from __future__ import annotations

from typing import Any

from .base_t2i import T2IResult, T2ITaskSubmission
from .jimeng_t2i import JimengT2IProvider
from .tongyi_t2i import TongyiWanxiangT2IProvider
from .dalle_t2i import DallET2IProvider
from .sd_t2i import StableDiffusionT2IProvider


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROVIDER_CLASSES: dict[str, type] = {
    "jimeng": JimengT2IProvider,
    "tongyi": TongyiWanxiangT2IProvider,
    "dalle": DallET2IProvider,
    "sd": StableDiffusionT2IProvider,
}

# Singleton instances (lazy initialised)
_PROVIDER_INSTANCES: dict[str, Any] = {}


def _get_instance(code: str) -> Any:
    """Return a singleton instance for the given provider code."""
    if code not in _PROVIDER_INSTANCES:
        cls = _PROVIDER_CLASSES.get(code)
        if cls is None:
            raise ValueError(f"Unknown provider code: {code}")
        _PROVIDER_INSTANCES[code] = cls()
    return _PROVIDER_INSTANCES[code]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class T2IDispatcher:
    """
    T2I 统一调度器

    用法示例::

        dispatcher = T2IDispatcher()

        # 同步生成
        result = dispatcher.generate(
            provider_code="jimeng",
            prompt="一只可爱的猫咪",
            config={"api_key": "xxx"},
        )

        # 异步提交（自动判断是否走 submit 还是 generate）
        submission = dispatcher.submit(
            provider_code="tongyi",
            prompt="一只可爱的猫咪",
            config={"api_key": "xxx"},
        )

        # 轮询
        result = dispatcher.poll(
            provider_code="tongyi",
            provider_task_id=submission.provider_task_id,
            config={"api_key": "xxx"},
        )

        # 列出所有 Provider
        providers = dispatcher.list_providers()
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        provider_code: str,
        prompt: str,
        config: dict[str, Any],
        negative_prompt: str | None = None,
        style: str | None = None,
        style_strength: float | None = None,
        image_size: str | None = None,
        num_images: int = 1,
        extra_params: dict[str, Any] | None = None,
    ) -> T2IResult:
        """
        同步生成图片。

        Parameters
        ----------
        provider_code: str
            Provider 标识，如 'jimeng'、'tongyi'、'dalle'、'sd'
        prompt: str
            图片生成提示词
        config: dict[str, Any]
            Provider 配置（如 api_key、base_url 等）
        negative_prompt: str | None
            反向提示词
        style: str | None
            画面风格
        style_strength: float | None
            风格强度 0.0~1.0
        image_size: str | None
            输出图像尺寸，如 '1024x1024'
        num_images: int
            生成数量（默认 1）
        extra_params: dict[str, Any] | None
            额外透传参数

        Returns
        -------
        T2IResult
        """
        provider = _get_instance(provider_code)
        return provider.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            style_strength=style_strength,
            image_size=image_size,
            num_images=num_images,
            config=config,
            extra_params=extra_params,
        )

    def submit(
        self,
        *,
        provider_code: str,
        prompt: str,
        config: dict[str, Any],
        negative_prompt: str | None = None,
        style: str | None = None,
        style_strength: float | None = None,
        image_size: str | None = None,
        num_images: int = 1,
        extra_params: dict[str, Any] | None = None,
    ) -> T2ITaskSubmission:
        """
        异步提交图片生成任务。

        内部逻辑：
        1. 获取 Provider 实例
        2. 调用 Provider.submit()
        3. 返回 T2ITaskSubmission

        注意：同步模式 Provider（dalle、sd）的 submit() 内部会直接调用
        generate() 并将结果包装为已完成的任务，因此无需额外 poll()。

        Parameters
        ----------
        provider_code: str
            Provider 标识
        prompt: str
            图片生成提示词
        config: dict[str, Any]
            Provider 配置
        其他参数同 generate()

        Returns
        -------
        T2ITaskSubmission
        """
        provider = _get_instance(provider_code)
        return provider.submit(
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            style_strength=style_strength,
            image_size=image_size,
            num_images=num_images,
            config=config,
            extra_params=extra_params,
        )

    def poll(
        self,
        *,
        provider_code: str,
        provider_task_id: str,
        config: dict[str, Any],
    ) -> T2IResult:
        """
        轮询异步任务状态。

        注意：同步模式 Provider（dalle、sd）的 poll() 默认返回失败，
        因为它们的 submit() 已经同步返回了完整结果，无需轮询。

        Parameters
        ----------
        provider_code: str
            Provider 标识
        provider_task_id: str
            上游任务 ID（由 submit() 返回）
        config: dict[str, Any]
            Provider 配置

        Returns
        -------
        T2IResult
        """
        provider = _get_instance(provider_code)
        return provider.poll(provider_task_id=provider_task_id, config=config)

    def list_providers(self) -> list[dict[str, Any]]:
        """
        返回所有已注册 Provider 的元信息列表。

        Returns
        -------
        list[dict[str, Any]]
            每个 Provider 的 metadata，包含：
            - code: str
            - display_name: str
            - description: str
            - capabilities: dict (来自 get_capabilities())
            - config_fields: list[dict] (来自 list_config_fields())
        """
        providers = []
        for code in _PROVIDER_CLASSES:
            instance = _get_instance(code)
            providers.append({
                "code": instance.code(),
                "display_name": instance.display_name(),
                "description": instance.description(),
                "capabilities": instance.get_capabilities(),
                "config_fields": [f.to_dict() for f in instance.list_config_fields()],
            })
        return providers

    def validate_provider_config(
        self,
        provider_code: str,
        config: dict[str, Any],
    ) -> list[str]:
        """
        校验指定 Provider 的配置。

        Parameters
        ----------
        provider_code: str
            Provider 标识
        config: dict[str, Any]
            待校验的配置

        Returns
        -------
        list[str]
            空列表表示校验通过，否则返回错误消息列表
        """
        provider = _get_instance(provider_code)
        return provider.validate_config(config)

    def healthcheck(
        self,
        provider_code: str,
        config: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        对指定 Provider 执行健康检查。

        Parameters
        ----------
        provider_code: str
        config: dict[str, Any]

        Returns
        -------
        tuple[bool, str | None]
            (是否健康, 错误消息或 None)
        """
        provider = _get_instance(provider_code)
        return provider.healthcheck(config)

    @staticmethod
    def supported_codes() -> list[str]:
        """返回所有支持的 provider_code 列表。"""
        return list(_PROVIDER_CLASSES.keys())
