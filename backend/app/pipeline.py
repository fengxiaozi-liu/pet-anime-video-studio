from __future__ import annotations

import threading
from pathlib import Path

from .jobs import JobStore
from .providers.cloud_dispatch import render_cloud
from .providers.local_provider import render_local


def run_job(job_id: str, store: JobStore) -> None:
    # Run in a background thread to keep it simple (WSL-friendly).
    t = threading.Thread(target=_run, args=(job_id, store), daemon=True)
    t.start()


def _run(job_id: str, store: JobStore) -> None:
    job = store.get(job_id)
    if not job:
        return

    store.patch(job_id, status="running", stage="preparing", status_text="准备渲染任务", error=None)

    try:
        out = Path(job["output"])
        out.parent.mkdir(parents=True, exist_ok=True)

        backend = job.get("backend", "auto")
        provider = job.get("provider", "kling")
        bgm = Path(job["bgm"]) if job.get("bgm") else None
        prompt = job.get("prompt") or ""
        storyboard = job["storyboard"]
        image_paths = [Path(p) for p in job["images"]]
        template_name = job.get("template_name") or storyboard.get("template_name")

        if backend == "local":
            store.patch(
                job_id,
                stage="rendering_local",
                status_text="使用本地链路渲染中",
                effective_backend="local",
                effective_provider=None,
                fallback_reason=None,
                template_name=template_name,
            )
            render_local(
                prompt=prompt,
                storyboard=storyboard,
                image_paths=image_paths,
                out_path=out,
                bgm_path=bgm,
            )
        elif backend == "cloud":
            store.patch(
                job_id,
                stage="rendering_cloud",
                status_text=f"使用云端提供商 {provider} 渲染中",
                effective_backend="cloud",
                effective_provider=provider,
                fallback_reason=None,
                template_name=template_name,
            )
            render_cloud(
                provider=provider,
                prompt=prompt,
                storyboard=storyboard,
                image_paths=image_paths,
                out_path=out,
                bgm_path=bgm,
            )
        elif backend == "auto":
            store.patch(
                job_id,
                stage="trying_cloud",
                status_text=f"Auto 模式：先尝试云端提供商 {provider}",
                effective_backend="cloud",
                effective_provider=provider,
                fallback_reason=None,
                template_name=template_name,
            )
            try:
                render_cloud(
                    provider=provider,
                    prompt=prompt,
                    storyboard=storyboard,
                    image_paths=image_paths,
                    out_path=out,
                    bgm_path=bgm,
                )
            except Exception as cloud_error:
                fallback_reason = str(cloud_error)
                store.patch(
                    job_id,
                    stage="fallback_local",
                    status_text="云端不可用，回退到本地链路",
                    effective_backend="local",
                    effective_provider=None,
                    fallback_reason=fallback_reason,
                    template_name=template_name,
                )
                render_local(
                    prompt=prompt,
                    storyboard=storyboard,
                    image_paths=image_paths,
                    out_path=out,
                    bgm_path=bgm,
                )
        else:
            raise ValueError(f"Unknown backend: {backend}")

        store.patch(job_id, status="done", stage="done", status_text="视频已生成完成", template_name=template_name)
    except Exception as e:
        store.patch(job_id, status="error", stage="error", status_text="生成失败", error=str(e))
