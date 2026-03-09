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

    store.patch(job_id, status="running", error=None)

    try:
        out = Path(job["output"])
        out.parent.mkdir(parents=True, exist_ok=True)

        backend = job.get("backend", "auto")
        provider = job.get("provider", "kling")
        bgm = Path(job["bgm"]) if job.get("bgm") else None

        if backend == "local":
            render_local(
                prompt=job.get("prompt") or "",
                storyboard=job["storyboard"],
                image_paths=[Path(p) for p in job["images"]],
                out_path=out,
                bgm_path=bgm,
            )
        elif backend == "cloud":
            render_cloud(
                provider=provider,
                prompt=job.get("prompt") or "",
                storyboard=job["storyboard"],
                image_paths=[Path(p) for p in job["images"]],
                out_path=out,
                bgm_path=bgm,
            )
        elif backend == "auto":
            try:
                render_cloud(
                    provider=provider,
                    prompt=job.get("prompt") or "",
                    storyboard=job["storyboard"],
                    image_paths=[Path(p) for p in job["images"]],
                    out_path=out,
                    bgm_path=bgm,
                )
            except Exception:
                # fallback to local for a guaranteed result
                render_local(
                    prompt=job.get("prompt") or "",
                    storyboard=job["storyboard"],
                    image_paths=[Path(p) for p in job["images"]],
                    out_path=out,
                    bgm_path=bgm,
                )
        else:
            raise ValueError(f"Unknown backend: {backend}")

        store.patch(job_id, status="done")
    except Exception as e:
        store.patch(job_id, status="error", error=str(e))
