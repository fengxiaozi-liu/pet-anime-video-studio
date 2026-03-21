from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JobStatus = str
AssetPath = str
ProviderTaskId = str
AspectRatio = str


@dataclass(slots=True)
class RenderJob:
    job_id: str
    backend: str
    provider_code: str
    provider_config_snapshot_json: dict[str, Any]
    prompt: str
    storyboard: dict[str, Any]
    images: list[str]
    bgm_path: str | None
    output_path: str
    status: JobStatus
    stage: str
    status_text: str
    effective_backend: str | None = None
    effective_provider: str | None = None
    fallback_reason: str | None = None
    error: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    platform: str | None = None
    final_video_url: str | None = None
    final_cover_url: str | None = None
    scene_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    scene_status_counts: dict[str, int] = field(default_factory=dict)
    scene_jobs: list[SceneJob] = field(default_factory=list)


@dataclass(slots=True)
class SceneJob:
    scene_job_id: str
    job_id: str
    scene_index: int
    provider_code: str
    provider_config_snapshot_json: dict[str, Any]
    scene_payload: dict[str, Any]
    provider_task_id: str | None = None
    provider_request_url: str | None = None
    provider_get_url: str | None = None
    provider_request_payload_json: dict[str, Any] = field(default_factory=dict)
    provider_response_payload_json: dict[str, Any] = field(default_factory=dict)
    provider_status: str | None = None
    normalized_status: JobStatus = "queued"
    result_video_url: str | None = None
    result_cover_url: str | None = None
    error: str | None = None
    last_polled_at: float | None = None
    poll_attempts: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass(slots=True)
class ProviderConfig:
    provider_code: str
    display_name: str
    enabled: bool
    sort_order: int
    description: str
    config_version: int
    provider_config_json: dict[str, Any]
    is_valid: bool
    last_checked_at: float | None
    last_error: str | None
    created_at: float
    updated_at: float
    id: int | None = None


@dataclass(slots=True)
class StoryAssistantConfig:
    assistant_code: str
    display_name: str
    enabled: bool
    sort_order: int
    description: str
    protocol: str
    base_url: str
    api_key: str
    model: str
    system_prompt: str
    temperature: float
    is_valid: bool
    last_checked_at: float | None
    last_error: str | None
    created_at: float
    updated_at: float
    id: int | None = None


@dataclass(slots=True)
class AssetBase:
    id: str
    name: str
    description: str
    path: AssetPath
    mime_type: str
    size_bytes: int
    enabled: bool
    sort_order: int
    created_at: float
    updated_at: float


@dataclass(slots=True)
class VisualAsset(AssetBase):
    prompt_fragment: str = ""
    cover_path: str | None = None


@dataclass(slots=True)
class CharacterAsset(AssetBase):
    prompt_fragment: str = ""
    image_path: str | None = None
    group_name: str = "默认分组"


@dataclass(slots=True)
class VoiceAsset(AssetBase):
    tone: str = ""
    audio_path: str | None = None
    sample_rate: int | None = None
    duration_ms: int | None = None


@dataclass(slots=True)
class MusicAsset(AssetBase):
    author: str = ""
    genre_tags: str = ""
    audio_path: str | None = None
    duration_ms: int | None = None
