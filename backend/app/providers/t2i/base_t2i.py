"""
TextToImage Provider 父子类架构

Parent: TextToImageProvider (ABC)
  - 定义统一接口：code / display_name / description / list_config_fields / validate_config / generate / submit / poll
  - 通用能力：healthcheck / get_capabilities / normalize_result
  - 默认实现：submit 调用 generate（同步模式 Provider 可只实现 generate）

Children: 各 Provider 实现
  - JimengT2IProvider  (即梦)
  - TongyiWanxiangT2IProvider  (通义万相)
  - DallET2IProvider  (OpenAI DALL-E)
  - StableDiffusionT2IProvider  (Stable Diffusion)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class T2IProviderField:
    """T2I Provider 配置字段"""

    key: str
    label: str
    kind: str = "text"
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    options: list[dict[str, str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
            "options": self.options,
        }


@dataclass(frozen=True)
class T2IResult:
    """
    T2I 生成结果

    image_url: 生成图片的访问 URL（可直接下载的公网 URL）
    image_b64:  base64 编码的图片数据（image_url 缺失时使用）
    normalized_prompt: 经过模型规范化后的提示词（便于追源）
    normalized_status: 统一状态 (pending / done / failed)
    raw_response: 上游接口原始响应（便于调试）
    """

    image_url: str | None = None
    image_b64: str | None = None
    normalized_prompt: str | None = None
    normalized_status: str = "pending"
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_url": self.image_url,
            "image_b64": self.image_b64,
            "normalized_prompt": self.normalized_prompt,
            "normalized_status": self.normalized_status,
            "raw_response": self.raw_response,
        }


@dataclass(frozen=True)
class T2ITaskSubmission:
    """
    异步任务提交结果

    provider_task_id: 上游任务 ID
    provider_status: 上游状态字符串
    normalized_status: 统一状态 (submitted / polling / done / failed)
    request_payload: 实际发送的请求体（便于调试）
    raw_response: 上游原始响应
    """

    provider_task_id: str
    provider_status: str
    normalized_status: str = "submitted"
    request_payload: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class TextToImageProvider(ABC):
    """
    Text-to-Image Provider 抽象基类（Parent）

    设计原则
    --------
    1. 同步模式 Provider（如 DALL-E、Stable Diffusion）只需实现 _do_generate()；
       submit / poll 使用默认实现（submit 调用 generate 并包装为已完成的任务记录）。
    2. 异步模式 Provider（如即梦、通义万相）实现 submit() + poll()。
    3. 所有 Provider 必须实现 code / display_name / description /
       list_config_fields / validate_config / _do_generate。
    4. normalize_result() 统一处理 image_url / image_b64 归一化并设置
       normalized_status，子类可覆盖以适配特殊响应结构。

    方法调用链
    ---------
    同步模式:
        generate() → _do_generate() → normalize_result()
        submit()   → generate() [= _do_generate() + normalize_result()]

    异步模式:
        submit() → 上游提交任务 → 返回 T2ITaskSubmission
        poll()   → 上游轮询 → normalize_result()
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @abstractmethod
    def code(self) -> str:
        """Provider 唯一标识，如 'jimeng'、'dalle'、'sd'"""
        raise NotImplementedError

    @abstractmethod
    def display_name(self) -> str:
        """用户可见的名称，如 '即梦'、'DALL-E'"""
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        """简短描述"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @abstractmethod
    def list_config_fields(self) -> list[T2IProviderField]:
        """返回 Provider 需要用户填写的配置字段列表"""
        raise NotImplementedError

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        校验配置完整性，返回空列表表示通过，否则返回错误消息列表。
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> dict[str, Any]:
        """
        返回 Provider 能力描述。子类可覆盖以补充特定能力。
        默认返回：

        {
            "supports_async": True,         # 是否支持异步提交+轮询
            "supports_sync": True,          # 是否支持同步生成（直接返回图片）
            "supports_styles": True,         # 是否支持 style/style_strength 参数
            "supports_negative_prompt": True,  # 是否支持反向提示词
            "supports_image_size": True,    # 是否支持指定图像尺寸
            "max_image_size": "1024x1024", # 最大图像尺寸
        }
        """
        return {
            "supports_async": True,
            "supports_sync": True,
            "supports_styles": True,
            "supports_negative_prompt": True,
            "supports_image_size": True,
            "max_image_size": "1024x1024",
        }

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def healthcheck(self, config: dict[str, Any]) -> tuple[bool, str | None]:
        """
        健康检查。默认基于 validate_config。
        子类可覆盖以实现真实的 API 连通性探测。
        """
        errors = self.validate_config(config)
        if errors:
            return False, "；".join(errors)
        return True, None

    # ------------------------------------------------------------------
    # Generation (sync)
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        prompt: str,
        negative_prompt: str | None = None,
        style: str | None = None,
        style_strength: float | None = None,
        image_size: str | None = None,
        num_images: int = 1,
        config: dict[str, Any],
        extra_params: dict[str, Any] | None = None,
    ) -> T2IResult:
        """
        同步生成图片。

        默认实现：调用 _do_generate() 执行实际的 API 请求，
        然后通过 normalize_result() 归一化结果。
        子类如需自定义请求逻辑可覆盖 _do_generate() 或直接覆盖 generate()。

        Parameters
        ----------
        prompt: str
            图片生成提示词
        negative_prompt: str | None
            反向提示词（告诉模型避免的内容）
        style: str | None
            画面风格，如 '动漫'、'写实'、'水彩'
        style_strength: float | None
            风格强度 0.0~1.0（部分 Provider 支持）
        image_size: str | None
            输出图像尺寸，如 '1024x1024'、'768x1344'
        num_images: int
            生成数量（默认 1）
        config: dict[str, Any]
            Provider 配置（从 job.provider_config_json 传入）
        extra_params: dict[str, Any] | None
            额外透传参数（如 seed、quality 等）

        Returns
        -------
        T2IResult
        """
        result = self._do_generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            style_strength=style_strength,
            image_size=image_size,
            num_images=num_images,
            config=config,
            extra_params=extra_params,
        )
        return self.normalize_result(result)

    # ------------------------------------------------------------------
    # Async workflow (submit + poll)
    # ------------------------------------------------------------------

    def submit(
        self,
        *,
        prompt: str,
        negative_prompt: str | None = None,
        style: str | None = None,
        style_strength: float | None = None,
        image_size: str | None = None,
        num_images: int = 1,
        config: dict[str, Any],
        extra_params: dict[str, Any] | None = None,
    ) -> T2ITaskSubmission:
        """
        异步提交图片生成任务。

        默认实现（同步模式）：
        直接调用 generate()（即 _do_generate() + normalize_result()），
        将结果包装为已完成的任务提交记录。
        适用于 DALL-E、Stable Diffusion 等同步返回结果的 Provider。

        异步模式 Provider（如即梦、通义万相）应覆盖此方法，
        真正向上游提交任务并返回带 task_id 的 T2ITaskSubmission。
        """
        result = self.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            style_strength=style_strength,
            image_size=image_size,
            num_images=num_images,
            config=config,
            extra_params=extra_params,
        )
        return T2ITaskSubmission(
            provider_task_id=f"sync-{self.code()}-{id(result)}",
            provider_status="done",
            normalized_status="done",
            request_payload={"prompt": prompt},
            raw_response=result.raw_response,
        )

    def poll(
        self,
        *,
        provider_task_id: str,
        config: dict[str, Any],
    ) -> T2IResult:
        """
        轮询异步任务状态。

        默认实现（同步模式 Provider）：
        返回失败结果。同步模式 Provider 不需要轮询，
        其 submit() 已通过 generate() 同步获取结果。

        异步模式 Provider（如即梦、通义万相）应覆盖此方法，
        真正向上游轮询任务状态并返回 T2IResult。
        """
        return T2IResult(
            normalized_status="failed",
            raw_response={
                "error": f"Provider {self.code()} does not support async polling "
                "(sync-only mode: use generate() directly)"
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers (可覆盖)
    # ------------------------------------------------------------------

    def _do_generate(
        self,
        *,
        prompt: str,
        negative_prompt: str | None,
        style: str | None,
        style_strength: float | None,
        image_size: str | None,
        num_images: int,
        config: dict[str, Any],
        extra_params: dict[str, Any] | None,
    ) -> T2IResult:
        """
        执行实际 API 请求的虚方法。

        默认实现：抛出 NotImplementedError。
        子类必须覆盖此方法，实现真正的 API 调用逻辑，
        返回包含 image_url / image_b64 / raw_response 的 T2IResult。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must override _do_generate() or generate()"
        )

    def normalize_result(self, result: T2IResult) -> T2IResult:
        """
        统一归一化结果。

        1. 若 result.image_url 或 result.image_b64 已非空，直接设置
           normalized_status="done" 并返回。
        2. 否则尝试从 raw_response 中提取图片（调用 _extract.py），
           提取成功则 normalized_status="done"，失败则 normalized_status="failed"。

        子类可覆盖以处理特殊响应结构。
        """
        if result.image_url or result.image_b64:
            return T2IResult(
                image_url=result.image_url,
                image_b64=result.image_b64,
                normalized_prompt=result.normalized_prompt,
                normalized_status="done",
                raw_response=result.raw_response,
            )

        # 尝试从 raw_response 中提取
        raw = result.raw_response or {}
        from ._extract import extract_image_from_response

        extracted = extract_image_from_response(raw)
        extracted_url = extracted.get("image_url", "")
        extracted_b64 = extracted.get("image_b64", "")
        status = "done" if (extracted_url or extracted_b64) else "failed"

        return T2IResult(
            image_url=extracted_url or None,
            image_b64=extracted_b64 or None,
            normalized_prompt=result.normalized_prompt,
            normalized_status=status,
            raw_response=result.raw_response,
        )
