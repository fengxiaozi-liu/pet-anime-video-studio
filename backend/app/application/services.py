from __future__ import annotations

import shutil
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..domain.models import ProviderConfig, RenderJob, SceneJob
from ..domain.repositories import RenderJobRepository, StorageService
from ..platform_templates import get_platform_template


class ProviderConfigService:
    def __init__(self, provider_repo, provider_registry, app_config) -> None:
        self.provider_repo = provider_repo
        self.provider_registry = provider_registry
        self.app_config = app_config

    def seed_from_config(self) -> None:
        for item in self.provider_registry.list_registered():
            provider = self.provider_registry.get(item["provider_code"])
            provider_cfg = self.app_config.providers.get(item["provider_code"], {})
            config = ProviderConfig(
                provider_code=item["provider_code"],
                display_name=item["display_name"],
                enabled=bool(provider_cfg.get("enabled", False)),
                sort_order=item["sort_order"],
                description=item["description"],
                config_version=1,
                provider_config_json={k: v for k, v in provider_cfg.items() if k != "enabled"},
                is_valid=not provider.validate_config({k: v for k, v in provider_cfg.items() if k != "enabled"}),
                last_checked_at=time.time(),
                last_error=None,
                created_at=time.time(),
                updated_at=time.time(),
            )
            self.provider_repo.seed(config)

    def list_configs_for_ui(self) -> list[dict[str, Any]]:
        current = {item.provider_code: item for item in self.provider_repo.list_all()}
        payload: list[dict[str, Any]] = []
        for item in self.provider_registry.list_registered():
            config = current.get(item["provider_code"])
            if config is None:
                config = ProviderConfig(
                    provider_code=item["provider_code"],
                    display_name=item["display_name"],
                    enabled=False,
                    sort_order=item["sort_order"],
                    description=item["description"],
                    config_version=1,
                    provider_config_json={},
                    is_valid=False,
                    last_checked_at=None,
                    last_error="尚未配置",
                    created_at=time.time(),
                    updated_at=time.time(),
                )
            payload.append({**asdict(config), "capabilities": item["capabilities"], "config_fields": item["config_fields"]})
        return payload

    def list_available(self) -> list[dict[str, Any]]:
        configs = {item.provider_code: item for item in self.provider_repo.list_all()}
        items: list[dict[str, Any]] = []
        for provider in self.provider_registry.list_registered():
            config = configs.get(provider["provider_code"])
            if config and config.enabled and config.is_valid:
                items.append(
                    {
                        "provider_code": provider["provider_code"],
                        "display_name": provider["display_name"],
                        "description": provider["description"],
                        "capabilities": provider["capabilities"],
                    }
                )
        return items

    def validate(self, provider_code: str, provider_config_json: dict[str, Any]) -> list[str]:
        return self.provider_registry.get(provider_code).validate_config(provider_config_json)

    def update(self, provider_code: str, *, enabled: bool, provider_config_json: dict[str, Any]) -> dict[str, Any]:
        registered = next(item for item in self.provider_registry.list_registered() if item["provider_code"] == provider_code)
        errors = self.validate(provider_code, provider_config_json)
        config = ProviderConfig(
            provider_code=provider_code,
            display_name=registered["display_name"],
            enabled=enabled,
            sort_order=registered["sort_order"],
            description=registered["description"],
            config_version=1,
            provider_config_json=provider_config_json,
            is_valid=not errors,
            last_checked_at=time.time(),
            last_error=None if not errors else "；".join(errors),
            created_at=time.time(),
            updated_at=time.time(),
        )
        stored = self.provider_repo.upsert(config)
        return asdict(stored)


class MaterialAssetService:
    def __init__(self, asset_repo, storage: StorageService) -> None:
        self.asset_repo = asset_repo
        self.storage = storage

    def list_materials(self, *, enabled_only: bool) -> dict[str, list[dict[str, Any]]]:
        return self.asset_repo.list_grouped(enabled_only=enabled_only)

    def create_asset(self, asset_type: str, metadata: dict[str, Any], *, file_name: str, file_bytes: bytes) -> dict[str, Any]:
        stored = self.storage.save_bytes(filename=file_name, data=file_bytes, category=asset_type)
        payload = {**metadata, "path": stored.path, "mime_type": stored.mime_type, "size_bytes": stored.size_bytes}
        if asset_type == "visuals":
            payload["cover_path"] = stored.path
        if asset_type == "characters":
            payload["image_path"] = stored.path
        if asset_type in {"voices", "music"}:
            payload["audio_path"] = stored.path
        return self.asset_repo.create_asset(asset_type, payload)

    def update_asset(self, asset_type: str, asset_id: str, metadata: dict[str, Any], *, file_name: str | None = None, file_bytes: bytes | None = None) -> dict[str, Any]:
        existing = self.asset_repo.get_asset(asset_type, asset_id)
        if existing is None:
            raise KeyError(asset_id)
        payload = dict(metadata)
        if file_name and file_bytes is not None:
            old_path = existing.get("path")
            stored = self.storage.save_bytes(filename=file_name, data=file_bytes, category=asset_type)
            payload.update({"path": stored.path, "mime_type": stored.mime_type, "size_bytes": stored.size_bytes})
            if asset_type == "visuals":
                payload["cover_path"] = stored.path
            if asset_type == "characters":
                payload["image_path"] = stored.path
            if asset_type in {"voices", "music"}:
                payload["audio_path"] = stored.path
            if old_path and old_path != stored.path:
                self.storage.delete(old_path)
        return self.asset_repo.update_asset(asset_type, asset_id, payload)

    def delete_asset(self, asset_type: str, asset_id: str) -> dict[str, Any] | None:
        deleted = self.asset_repo.delete_asset(asset_type, asset_id)
        if deleted and deleted.get("path"):
            self.storage.delete(deleted["path"])
        return deleted


class JobApplicationService:
    def __init__(self, render_repo: RenderJobRepository, scene_repo, provider_repo, asset_repo, app_config) -> None:
        self.render_repo = render_repo
        self.scene_repo = scene_repo
        self.provider_repo = provider_repo
        self.asset_repo = asset_repo
        self.app_config = app_config

    def create_job(
        self,
        *,
        prompt: str,
        provider: str,
        backend: str,
        storyboard: dict[str, Any],
        template_id: str | None,
        bgm_path: str | None,
        output_path: str,
        images: list[str],
    ) -> str:
        if provider != "jimeng":
            raise ValueError("当前仅支持 jimeng provider。")
        provider_meta = self.provider_repo.get(provider)
        if provider_meta is None or not provider_meta.enabled or not provider_meta.is_valid:
            raise ValueError(f"Provider {provider} 未配置或未启用。")

        visual_asset = None
        visual_asset_id = storyboard.get("visual_asset_id") or storyboard.get("visual_style_id")
        if visual_asset_id:
            visual_asset = self.asset_repo.get_asset("visuals", visual_asset_id)
            if visual_asset:
                storyboard["visual_asset_id"] = visual_asset["id"]
                storyboard["visual_asset_path"] = visual_asset["path"]
                storyboard["visual_asset_url"] = visual_asset.get("public_url")
                storyboard["style_prompt"] = visual_asset.get("prompt_fragment") or storyboard.get("style_prompt", "")

        selected_characters = []
        for char_id in storyboard.get("character_ids", []):
            item = self.asset_repo.get_asset("characters", char_id)
            if item:
                selected_characters.append(item)
        storyboard["selected_characters"] = selected_characters

        voice_id = storyboard.get("voice_id")
        if voice_id:
            voice_asset = self.asset_repo.get_asset("voices", voice_id)
            if voice_asset:
                storyboard["voice_asset"] = voice_asset
        music_id = storyboard.get("music_id")
        if music_id:
            music_asset = self.asset_repo.get_asset("music", music_id)
            if music_asset:
                storyboard["music_asset"] = music_asset

        job_id = str(uuid.uuid4())
        now = time.time()
        scenes_payload = list(storyboard.get("scenes") or [])
        character_prompt_map = {item["id"]: item.get("prompt_fragment") or "" for item in selected_characters}
        for scene in scenes_payload:
            scene_character_ids = list(scene.get("character_ids") or storyboard.get("character_ids") or [])
            scene["character_ids"] = scene_character_ids
            scene["character_prompt_fragments"] = [
                character_prompt_map[char_id]
                for char_id in scene_character_ids
                if character_prompt_map.get(char_id)
            ]
            scene["visual_asset_id"] = scene.get("visual_asset_id") or storyboard.get("visual_asset_id")
            scene["visual_asset_url"] = scene.get("visual_asset_url") or storyboard.get("visual_asset_url")
        render_job = RenderJob(
            job_id=job_id,
            backend=backend,
            provider_code=provider,
            provider_config_snapshot_json=provider_meta.provider_config_json,
            prompt=prompt,
            storyboard=storyboard,
            images=images,
            bgm_path=bgm_path,
            output_path=output_path,
            status="queued",
            stage="queued",
            status_text="任务已创建，等待分镜任务提交",
            effective_backend=backend,
            template_id=template_id or storyboard.get("template_id"),
            template_name=storyboard.get("template_name"),
            platform=storyboard.get("platform"),
            scene_count=len(scenes_payload),
            created_at=now,
            updated_at=now,
        )
        self.render_repo.create(render_job)
        scene_jobs = []
        for index, scene in enumerate(scenes_payload):
            scene_jobs.append(
                SceneJob(
                    scene_job_id=f"{job_id}:scene:{index}",
                    job_id=job_id,
                    scene_index=index,
                    provider_code=provider,
                    provider_config_snapshot_json=provider_meta.provider_config_json,
                    scene_payload=scene,
                    normalized_status="queued",
                    created_at=now,
                    updated_at=now,
                )
            )
        self.scene_repo.create_many(scene_jobs)
        return job_id

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        return [asdict(job) for job in self.render_repo.list_recent(limit)]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.render_repo.refresh_status(job_id)
        return asdict(job) if job else None

    def delete_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.render_repo.delete(job_id)
        if job is None:
            return None
        payload = asdict(job)
        output_path = Path(job.output_path)
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        if job.final_cover_url:
            cover_path = Path(job.final_cover_url)
            if cover_path.exists():
                cover_path.unlink(missing_ok=True)
        if job.bgm_path:
            bgm_path = Path(job.bgm_path)
            if bgm_path.exists():
                bgm_path.unlink(missing_ok=True)
        upload_dir = Path(self.app_config.UPLOAD_DIR) / job_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        return payload
