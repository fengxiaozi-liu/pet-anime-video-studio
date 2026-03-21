from __future__ import annotations

import mimetypes
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetStoredResult:
    path: str
    mime_type: str
    size_bytes: int
    public_url: str


class LocalStorageService:
    def __init__(self, *, base_dir: Path, public_base_url: str) -> None:
        self.base_dir = base_dir
        self.public_base_url = public_base_url.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, filename: str, data: bytes, category: str) -> AssetStoredResult:
        suffix = Path(filename).suffix
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        relative = Path(category) / safe_name
        full_path = self.base_dir / relative
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return AssetStoredResult(
            path=str(relative).replace("\\", "/"),
            mime_type=mime_type,
            size_bytes=len(data),
            public_url=self.to_public_url(str(relative).replace("\\", "/")),
        )

    def copy_file(self, *, source: Path, category: str) -> AssetStoredResult:
        suffix = source.suffix
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        relative = Path(category) / safe_name
        full_path = self.base_dir / relative
        full_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, full_path)
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        return AssetStoredResult(
            path=str(relative).replace("\\", "/"),
            mime_type=mime_type,
            size_bytes=full_path.stat().st_size,
            public_url=self.to_public_url(str(relative).replace("\\", "/")),
        )

    def delete(self, path: str) -> None:
        full_path = self.base_dir / path
        if full_path.exists():
            full_path.unlink(missing_ok=True)

    def exists(self, path: str) -> bool:
        return (self.base_dir / path).exists()

    def to_public_url(self, path: str) -> str:
        return f"{self.public_base_url}/{path.lstrip('/')}"
