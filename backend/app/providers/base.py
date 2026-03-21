from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderField:
    key: str
    label: str
    kind: str = "text"
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
        }


@dataclass(frozen=True)
class ProviderTaskSubmission:
    provider_task_id: str
    provider_status: str
    normalized_status: str
    request_url: str
    get_url: str
    request_payload: dict[str, Any]
    raw_response: dict[str, Any]


@dataclass(frozen=True)
class ProviderTaskState:
    provider_status: str
    normalized_status: str
    raw_response: dict[str, Any]
    result_video_url: str | None = None
    result_cover_url: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class SceneTaskContext:
    job_id: str
    prompt: str
    scene_index: int
    scene_payload: dict[str, Any]
    storyboard: dict[str, Any]
    working_dir: Path


@dataclass(frozen=True)
class RenderContext:
    provider: str
    prompt: str
    storyboard: dict[str, Any]
    image_paths: list[Path]
    out_path: Path
    bgm_path: Path | None = None


class BaseProvider(ABC):
    @abstractmethod
    def code(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_config_fields(self) -> list[ProviderField]:
        raise NotImplementedError

    @abstractmethod
    def validate_config(self, provider_config_json: dict[str, Any]) -> list[str]:
        raise NotImplementedError

    def healthcheck(self, provider_config_json: dict[str, Any]) -> tuple[bool, str | None]:
        errors = self.validate_config(provider_config_json)
        return (not errors, None if not errors else "；".join(errors))

    def get_capabilities(self) -> dict[str, Any]:
        return {"supports_async_tasks": True, "supports_scene_video": True}

    @abstractmethod
    def create_task(
        self,
        scene: SceneTaskContext,
        provider_config_json: dict[str, Any],
    ) -> ProviderTaskSubmission:
        raise NotImplementedError

    @abstractmethod
    def get_task(
        self,
        provider_task_id: str,
        provider_config_json: dict[str, Any],
        scene_job: dict[str, Any] | None = None,
    ) -> ProviderTaskState:
        raise NotImplementedError

    def update_task(self, scene_job: dict[str, Any], provider_task_result: ProviderTaskState) -> dict[str, Any]:
        return {
            "provider_status": provider_task_result.provider_status,
            "normalized_status": provider_task_result.normalized_status,
            "provider_response_payload_json": provider_task_result.raw_response,
            "result_video_url": provider_task_result.result_video_url,
            "result_cover_url": provider_task_result.result_cover_url,
            "error": provider_task_result.error,
        }
