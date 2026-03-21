from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .base import BaseProvider, ProviderField, ProviderTaskState, ProviderTaskSubmission, SceneTaskContext
from .mock_clip import build_mock_clip


JIMENG_SUBMIT_URL = "https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31"
JIMENG_GET_URL = "https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31"


class JimengProvider(BaseProvider):
    def code(self) -> str:
        return "jimeng"

    def display_name(self) -> str:
        return "即梦"

    def description(self) -> str:
        return "火山引擎即梦视频生成 Provider，采用异步任务提交与轮询结果。"

    def list_config_fields(self) -> list[ProviderField]:
        return [
            ProviderField("app_key", "App Key", kind="password", required=True),
            ProviderField("app_secret", "App Secret", kind="password", required=True),
            ProviderField("req_key", "Req Key", required=False, placeholder="jimeng_ti2v_v30_pro"),
            ProviderField("base_url", "Base URL", required=False, placeholder="https://visual.volcengineapi.com"),
        ]

    def validate_config(self, provider_config_json: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not provider_config_json.get("app_key"):
            errors.append("缺少 app_key")
        if not provider_config_json.get("app_secret"):
            errors.append("缺少 app_secret")
        return errors

    def _is_mock_mode(self, provider_config_json: dict[str, Any]) -> bool:
        return bool(provider_config_json.get("mock_mode"))

    def _resolve_aspect_ratio(self, scene: SceneTaskContext) -> str:
        explicit_ratio = str(scene.storyboard.get("aspect_ratio") or "").strip()
        if explicit_ratio:
            return explicit_ratio
        width = int(scene.storyboard.get("width", 0) or 0)
        height = int(scene.storyboard.get("height", 0) or 0)
        if width > 0 and height > 0:
            known = {
                (16, 9): "16:9",
                (9, 16): "9:16",
                (1, 1): "1:1",
                (4, 3): "4:3",
                (3, 4): "3:4",
                (21, 9): "21:9",
            }
            ratio = width / height
            for pair, label in known.items():
                if abs(ratio - (pair[0] / pair[1])) < 0.03:
                    return label
            return f"{width}:{height}"
        raise ValueError("aspect_ratio missing and width/height unavailable")

    def _build_prompt(self, scene: SceneTaskContext) -> str:
        parts: list[str] = []
        scene_prompt = str(scene.scene_payload.get("prompt") or scene.prompt or "").strip()
        style_prompt = str(scene.storyboard.get("style_prompt") or "").strip()
        story_summary = str(scene.storyboard.get("story_summary") or "").strip()
        character_fragments = [
            str(item).strip()
            for item in (scene.scene_payload.get("character_prompt_fragments") or [])
            if str(item).strip()
        ]
        if scene_prompt:
            parts.append(scene_prompt)
        if style_prompt:
            parts.append(f"visual style: {style_prompt}")
        if character_fragments:
            parts.append(f"characters: {'; '.join(character_fragments)}")
        if story_summary:
            parts.append(f"story context: {story_summary}")
        return "\n".join(parts).strip()

    def _resolve_visual_asset_url(self, scene: SceneTaskContext) -> str | None:
        candidates = [
            scene.scene_payload.get("visual_asset_url"),
            scene.storyboard.get("visual_asset_url"),
        ]
        for value in candidates:
            candidate = str(value or "").strip()
            if not candidate:
                continue
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return candidate
        return None

    def _resolve_reference_image_urls(self, scene: SceneTaskContext) -> list[str]:
        urls: list[str] = []
        frame_candidates = [
            scene.scene_payload.get("opening_frame_url"),
            scene.storyboard.get("opening_frame_url"),
        ]
        for value in frame_candidates:
            candidate = str(value or "").strip()
            if not candidate:
                continue
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"} and parsed.netloc and candidate not in urls:
                urls.append(candidate)
        visual_asset_url = self._resolve_visual_asset_url(scene)
        if visual_asset_url:
            urls.append(visual_asset_url)
        for value in (scene.scene_payload.get("character_image_urls") or scene.storyboard.get("character_image_urls") or []):
            candidate = str(value or "").strip()
            if not candidate:
                continue
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"} and parsed.netloc and candidate not in urls:
                urls.append(candidate)
        ending_candidates = [
            scene.scene_payload.get("ending_frame_url"),
            scene.storyboard.get("ending_frame_url"),
        ]
        for value in ending_candidates:
            candidate = str(value or "").strip()
            if not candidate:
                continue
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"} and parsed.netloc and candidate not in urls:
                urls.append(candidate)
        return urls

    def create_task(
        self,
        scene: SceneTaskContext,
        provider_config_json: dict[str, Any],
    ) -> ProviderTaskSubmission:
        req_key = provider_config_json.get("req_key") or "jimeng_ti2v_v30_pro"
        width = int(scene.storyboard.get("width", 1280))
        height = int(scene.storyboard.get("height", 720))
        duration_s = float(scene.scene_payload.get("duration_s", 4))
        frames = 121 if duration_s <= 5 else 241
        prompt = self._build_prompt(scene)
        if not prompt:
            raise ValueError("scene prompt is empty")

        payload = {
            "req_key": req_key,
            "prompt": prompt,
            "seed": -1,
            "frames": frames,
            "aspect_ratio": self._resolve_aspect_ratio(scene),
        }
        reference_image_urls = self._resolve_reference_image_urls(scene)
        if reference_image_urls:
            payload["image_urls"] = reference_image_urls

        if self._is_mock_mode(provider_config_json):
            task_id = f"jimeng-mock-{uuid.uuid4()}"
            clip_path = build_mock_clip(
                provider_code=self.code(),
                prompt=payload["prompt"],
                width=width,
                height=height,
                duration_s=duration_s,
                output_path=scene.working_dir / f"scene_{scene.scene_index:02d}_jimeng.mp4",
            )
            return ProviderTaskSubmission(
                provider_task_id=task_id,
                provider_status="in_queue",
                normalized_status="submitted",
                request_url=JIMENG_SUBMIT_URL,
                get_url=JIMENG_GET_URL,
                request_payload=payload,
                raw_response={
                    "task_id": task_id,
                    "mock": True,
                    "mock_video_url": clip_path.as_uri(),
                    "submitted_at": time.time(),
                },
            )

        raise NotImplementedError("Jimeng provider real API signing is not wired yet. Configure mock_mode for local integration.")

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
                    "status": "done",
                    "video_url": raw_response.get("mock_video_url"),
                    "task_id": provider_task_id,
                    "mock": True,
                },
                result_video_url=raw_response.get("mock_video_url"),
            )

        raise NotImplementedError("Jimeng provider real polling is not wired yet. Configure mock_mode for local integration.")
