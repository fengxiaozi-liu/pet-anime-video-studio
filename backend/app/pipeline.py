from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from .providers.base import SceneTaskContext
from .providers.cloud_dispatch import get_provider
from .providers.local_provider import compose_remote_clips


logger = logging.getLogger(__name__)


def run_job(job_id: str, render_repo) -> None:
    render_repo.patch(job_id, status="queued", stage="queued", status_text="任务已加入队列，等待分镜任务提交")


class TaskWorker:
    def __init__(
        self,
        *,
        render_repo,
        scene_repo,
        app_config,
        poll_interval_s: float = 2.0,
        compose_enabled: bool = True,
    ) -> None:
        self.render_repo = render_repo
        self.scene_repo = scene_repo
        self.app_config = app_config
        self.poll_interval_s = poll_interval_s
        self.compose_enabled = compose_enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="task-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.exception("Task worker tick failed: %s", exc)
            self._stop.wait(self.poll_interval_s)

    def _tick(self) -> None:
        self._submit_queued_scenes()
        self._poll_active_scenes()
        if self.compose_enabled:
            self._compose_ready_jobs()

    def _submit_queued_scenes(self) -> None:
        for scene_job in self.scene_repo.list_by_status(["queued"], limit=10):
            render_job = self.render_repo.get(scene_job.job_id)
            if not render_job:
                continue
            provider = get_provider(scene_job.provider_code)
            try:
                submission = provider.create_task(
                    SceneTaskContext(
                        job_id=render_job.job_id,
                        prompt=render_job.prompt or "",
                        scene_index=scene_job.scene_index,
                        scene_payload=scene_job.scene_payload,
                        storyboard=render_job.storyboard,
                        working_dir=Path(self.app_config.UPLOAD_DIR) / render_job.job_id,
                    ),
                    scene_job.provider_config_snapshot_json,
                )
                self.scene_repo.patch(
                    scene_job.scene_job_id,
                    provider_task_id=submission.provider_task_id,
                    provider_status=submission.provider_status,
                    normalized_status=submission.normalized_status,
                    provider_request_url=submission.request_url,
                    provider_get_url=submission.get_url,
                    provider_request_payload_json=submission.request_payload,
                    provider_response_payload_json=submission.raw_response,
                    error=None,
                )
            except Exception as exc:
                self.scene_repo.patch(
                    scene_job.scene_job_id,
                    normalized_status="failed",
                    provider_status="error",
                    error=str(exc),
                )
            self.render_repo.refresh_status(scene_job.job_id)

    def _poll_active_scenes(self) -> None:
        for scene_job in self.scene_repo.list_by_status(["submitted", "running"], limit=20):
            if not scene_job.provider_task_id:
                self.scene_repo.patch(scene_job.scene_job_id, normalized_status="failed", error="provider_task_id missing")
                self.render_repo.refresh_status(scene_job.job_id)
                continue
            provider = get_provider(scene_job.provider_code)
            try:
                task_state = provider.get_task(
                    scene_job.provider_task_id,
                    scene_job.provider_config_snapshot_json,
                    {
                        "scene_job_id": scene_job.scene_job_id,
                        "provider_response_payload_json": scene_job.provider_response_payload_json,
                        "poll_attempts": scene_job.poll_attempts,
                    },
                )
                patch_fields = provider.update_task(
                    {
                        "scene_job_id": scene_job.scene_job_id,
                        "provider_response_payload_json": scene_job.provider_response_payload_json,
                    },
                    task_state,
                )
                patch_fields["last_polled_at"] = time.time()
                patch_fields["poll_attempts"] = int(scene_job.poll_attempts or 0) + 1
                self.scene_repo.patch(scene_job.scene_job_id, **patch_fields)
            except Exception as exc:
                self.scene_repo.patch(
                    scene_job.scene_job_id,
                    normalized_status="failed",
                    provider_status="error",
                    error=str(exc),
                    last_polled_at=time.time(),
                    poll_attempts=int(scene_job.poll_attempts or 0) + 1,
                )
            self.render_repo.refresh_status(scene_job.job_id)

    def _compose_ready_jobs(self) -> None:
        for job in self.render_repo.list_ready_for_composition(limit=5):
            if job.status == "done":
                continue
            try:
                self.render_repo.patch(job.job_id, status="composing", stage="composing", status_text="开始拼接分镜视频")
                out_path = Path(job.output_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                bgm_path = Path(job.bgm_path) if job.bgm_path else None
                scene_video_urls = [scene.result_video_url for scene in job.scene_jobs if scene.result_video_url]
                compose_remote_clips(
                    storyboard=job.storyboard,
                    scene_video_urls=scene_video_urls,
                    out_path=out_path,
                    bgm_path=bgm_path,
                )
                cover_path = out_path.with_suffix(".cover.png")
                self.render_repo.patch(
                    job.job_id,
                    status="done",
                    stage="done",
                    status_text="视频已合成完成",
                    final_video_url=str(out_path),
                    final_cover_url=str(cover_path) if cover_path.exists() else None,
                    effective_backend="cloud",
                    effective_provider=job.provider_code,
                    error=None,
                )
            except Exception as exc:
                self.render_repo.patch(job.job_id, status="failed", stage="failed", status_text="视频合成失败", error=str(exc))
