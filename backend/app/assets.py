from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AssetStore:
    root_dir: Path
    index_path: Path
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _load(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text("utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(self.index_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.index_path)

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            data = self._load()
            items = list(data.values())
            items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return items[:limit]

    def get(self, asset_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._load().get(asset_id)

    def add(self, *, kind: str, filename: str, suffix: str, bytes_data: bytes) -> dict[str, Any]:
        asset_id = uuid.uuid4().hex
        now = time.time()  # float for sub-second precision
        self.root_dir.mkdir(parents=True, exist_ok=True)
        out = self.root_dir / f"{asset_id}{suffix}"
        out.write_bytes(bytes_data)

        meta = {
            "asset_id": asset_id,
            "kind": kind,
            "filename": filename,
            "path": str(out),
            "size": len(bytes_data),
            "created_at": now,
        }

        with self._lock:
            data = self._load()
            data[asset_id] = meta
            self._save(data)

        return meta
