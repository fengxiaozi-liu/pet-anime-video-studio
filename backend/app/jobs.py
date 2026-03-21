from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import threading


@dataclass
class JobStore:
    path: Path
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text("utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.path)

    def create(
        self,
        job_id: str,
        backend: str,
        provider: str,
        prompt: str,
        storyboard: dict[str, Any],
        images: list[str],
        bgm: str | None,
        output: str,
        **extra_fields: Any,
    ) -> None:
        with self._lock:
            data = self._load()
            if job_id in data:
                raise ValueError("job exists")
            now = time.time()  # float for sub-second precision
            data[job_id] = {
                "job_id": job_id,
                "backend": backend,
                "provider": provider,
                "prompt": prompt,
                "storyboard": storyboard,
                "images": images,
                "bgm": bgm,
                "output": output,
                "status": "queued",
                "stage": "queued",
                "status_text": "任务已创建，等待开始",
                "effective_backend": None,
                "effective_provider": None,
                "fallback_reason": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
                **extra_fields,
            }
            self._save(data)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._load().get(job_id)

    def list_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            data = self._load()
            items = list(data.values())
            items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return items[:limit]

    def patch(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            data = self._load()
            job = data.get(job_id)
            if not job:
                raise KeyError(job_id)
            job.update(fields)
            job["updated_at"] = time.time()
            data[job_id] = job
            self._save(data)

    def delete(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._load()
            job = data.pop(job_id, None)
            if job is None:
                return None
            self._save(data)
            return job
