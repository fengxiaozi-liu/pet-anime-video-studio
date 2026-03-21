from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .base import BaseProvider, ProviderField, ProviderTaskState, ProviderTaskSubmission, SceneTaskContext
from .mock_clip import build_mock_clip


class OpenAIProvider(BaseProvider):
    def code(self) -> str:
        return "openai"

    def display_name(self) -> str:
        return "OpenAI"

    def description(self) -> str:
        return "OpenAI 视频 Provider 模板实现，采用与即梦一致的异步任务抽象。"

    def list_config_fields(self) -> list[ProviderField]:
        return [
            ProviderField("api_key", "API Key", kind="password", required=True),
            ProviderField("model", "Model", required=True, placeholder="gpt-video-1"),
            ProviderField("base_url", "Base URL", required=False, placeholder="https://api.openai.com"),
            ProviderField("mock_mode", "Mock Mode", kind="checkbox", required=False, help_text="本地模拟 OpenAI 结果，便于联调。"),
        ]

    def validate_config(self, provider_config_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not provider_config_json.get("api_key"):
            errors.append("缺少 api_key")
        if not provider_config_json.get("model"):
            errors.append("缺少 model")
        return errors

    def _is_mock_mode(self, provider_config_json: dict[str, Any]) -> bool:
        return bool(provider_config_json.get("mock_mode"))

    def create_task(
        self,
        scene: SceneTaskContext,
        provider_config_json: dict[str, Any],
    ) -> ProviderTaskSubmission:
        payload = {
            "model": provider_config_json.get("model"),
            "prompt": scene.scene_payload.get("prompt") or scene.prompt,
            "duration_s": scene.scene_payload.get("duration_s", 4),
            "size": {
                "width": int(scene.storyboard.get("width", 1280)),
                "height": int(scene.storyboard.get("height", 720)),
            },
        }
        if self._is_mock_mode(provider_config_json):
            task_id = f"openai-mock-{uuid.uuid4()}"
            clip_path = build_mock_clip(
                provider_code=self.code(),
                prompt=payload["prompt"],
                width=payload["size"]["width"],
                height=payload["size"]["height"],
                duration_s=float(payload["duration_s"]),
                output_path=scene.working_dir / f"scene_{scene.scene_index:02d}_openai.mp4",
            )
            return ProviderTaskSubmission(
                provider_task_id=task_id,
                provider_status="queued",
                normalized_status="submitted",
                request_url=(provider_config_json.get("base_url") or "https://api.openai.com") + "/v1/video/tasks",
                get_url=(provider_config_json.get("base_url") or "https://api.openai.com") + f"/v1/video/tasks/{task_id}",
                request_payload=payload,
                raw_response={
                    "id": task_id,
                    "mock": True,
                    "mock_video_url": clip_path.as_uri(),
                    "submitted_at": time.time(),
                },
            )
        raise NotImplementedError("OpenAI provider real API integration is not wired yet. Configure mock_mode for local integration.")

    def get_task(
        self,
        provider_task_id: str,
        provider_config_json: dict[str, Any],
        scene_job: dict[str, Any] | None = None,
    ) -> ProviderTaskState:
        if self._is_mock_mode(provider_config_json):
            raw_response = scene_job.get("provider_response_payload_json") if scene_job else {}
            return ProviderTaskState(
                provider_status="done",
                normalized_status="succeeded",
                raw_response={
                    "id": provider_task_id,
                    "status": "done",
                    "video_url": raw_response.get("mock_video_url"),
                    "mock": True,
                },
                result_video_url=raw_response.get("mock_video_url"),
            )
        raise NotImplementedError("OpenAI provider real polling is not wired yet. Configure mock_mode for local integration.")
