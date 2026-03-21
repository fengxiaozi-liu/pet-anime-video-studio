from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from .jobs import JobStore
from .providers.base import SceneTaskContext
from .providers.cloud_dispatch import get_provider
from .providers.local_provider import compose_remote_clips


logger = logging.getLogger(__name__)


def run_job(job_id: str, store: JobStore) -> None:
    store.patch(job_id, status="queued", stage="queued", status_text="任务已加入队列，等待分镜任务提交")


class TaskWorker:
    def __init__(self, *, store: JobStore, upload_dir: Path, poll_interval_s: float = 2.0) -> None:
        self.store = store
        self.upload_dir = upload_dir
        self.poll_interval_s = poll_interval_s
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
        self._compose_ready_jobs()

    def _submit_queued_scenes(self) -> None:
        for scene_job in self.store.list_scene_jobs_by_status(["queued"], limit=10):
            render_job = self.store.get(scene_job["job_id"])
            if not render_job:
                continue
            provider = get_provider(scene_job["provider_code"])
            try:
                submission = provider.create_task(
                    SceneTaskContext(
                        job_id=render_job["job_id"],
                        prompt=render_job.get("prompt") or "",
                        scene_index=scene_job["scene_index"],
                        scene_payload=scene_job["scene_payload"],
                        storyboard=render_job["storyboard"],
                        working_dir=self.upload_dir / render_job["job_id"],
                    ),
                    scene_job["provider_config_snapshot_json"],
                )
                self.store.patch_scene_job(
                    scene_job["scene_job_id"],
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
                self.store.patch_scene_job(
                    scene_job["scene_job_id"],
                    normalized_status="failed",
                    provider_status="error",
                    error=str(exc),
                )
            self.store.refresh_render_job_status(scene_job["job_id"])

    def _poll_active_scenes(self) -> None:
        for scene_job in self.store.list_scene_jobs_by_status(["submitted", "running"], limit=20):
            provider_task_id = scene_job.get("provider_task_id")
            if not provider_task_id:
                self.store.patch_scene_job(scene_job["scene_job_id"], normalized_status="failed", error="provider_task_id missing")
                self.store.refresh_render_job_status(scene_job["job_id"])
                continue
            provider = get_provider(scene_job["provider_code"])
            try:
                task_state = provider.get_task(
                    provider_task_id,
                    scene_job["provider_config_snapshot_json"],
                    scene_job,
                )
                patch_fields = provider.update_task(scene_job, task_state)
                patch_fields["last_polled_at"] = time.time()
                patch_fields["poll_attempts"] = int(scene_job.get("poll_attempts") or 0) + 1
                self.store.patch_scene_job(scene_job["scene_job_id"], **patch_fields)
            except Exception as exc:
                self.store.patch_scene_job(
                    scene_job["scene_job_id"],
                    normalized_status="failed",
                    provider_status="error",
                    error=str(exc),
                    last_polled_at=time.time(),
                    poll_attempts=int(scene_job.get("poll_attempts") or 0) + 1,
                )
            self.store.refresh_render_job_status(scene_job["job_id"])

    def _compose_ready_jobs(self) -> None:
        for job in self.store.list_jobs_ready_for_composition(limit=5):
            if job["status"] == "done":
                continue
            try:
                self.store.patch(job["job_id"], status="composing", stage="composing", status_text="开始拼接分镜视频")
                out_path = Path(job["output"])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                bgm_path = Path(job["bgm"]) if job.get("bgm") else None
                scene_video_urls = [scene["result_video_url"] for scene in job["scene_jobs"] if scene.get("result_video_url")]
                compose_remote_clips(
                    storyboard=job["storyboard"],
                    scene_video_urls=scene_video_urls,
                    out_path=out_path,
                    bgm_path=bgm_path,
                )
                cover_path = out_path.with_suffix(".cover.png")
                if cover_path.exists():
                    final_cover_url = str(cover_path)
                else:
                    final_cover_url = None
                self.store.patch(
                    job["job_id"],
                    status="done",
                    stage="done",
                    status_text="视频已合成完成",
                    final_video_url=str(out_path),
                    final_cover_url=final_cover_url,
                    effective_backend="cloud",
                    effective_provider=job["provider_code"],
                    error=None,
                )
            except Exception as exc:
                self.store.patch(job["job_id"], status="failed", stage="failed", status_text="视频合成失败", error=str(exc))

