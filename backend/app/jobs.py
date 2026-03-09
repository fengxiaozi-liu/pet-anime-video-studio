from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class JobStore:
    path: Path

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
    ) -> None:
        data = self._load()
        if job_id in data:
            raise ValueError("job exists")
        now = int(time.time())
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
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        self._save(data)

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self._load().get(job_id)

    def patch(self, job_id: str, **fields: Any) -> None:
        data = self._load()
        job = data.get(job_id)
        if not job:
            raise KeyError(job_id)
        job.update(fields)
        job["updated_at"] = int(time.time())
        data[job_id] = job
        self._save(data)
