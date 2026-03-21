from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"


class AppSection(BaseModel):
    debug: bool = False
    data_dir: str = ".data"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"


class SqliteSection(BaseModel):
    path: str = ".data/tasks.db"


class MysqlSection(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    db: str = "petclip"
    user: str = "root"
    password: str = ""


class DatabaseSection(BaseModel):
    driver: str = "sqlite"
    sqlite: SqliteSection = Field(default_factory=SqliteSection)
    mysql: MysqlSection = Field(default_factory=MysqlSection)


class LocalStorageSection(BaseModel):
    base_dir: str = "uploads/assets"
    public_base_url: str = "http://127.0.0.1:8000/media"


class StorageSection(BaseModel):
    provider: str = "local"
    local: LocalStorageSection = Field(default_factory=LocalStorageSection)


class WorkerSection(BaseModel):
    poll_interval_s: float = 2.0
    max_retry: int = 20
    compose_enabled: bool = True


class AppConfig(BaseModel):
    app: AppSection = Field(default_factory=AppSection)
    database: DatabaseSection = Field(default_factory=DatabaseSection)
    storage: StorageSection = Field(default_factory=StorageSection)
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    worker: WorkerSection = Field(default_factory=WorkerSection)

    @property
    def DEBUG(self) -> bool:
        return self.app.debug

    @property
    def DATA_DIR(self) -> Path:
        return _resolve_path(self.app.data_dir)

    @property
    def UPLOAD_DIR(self) -> Path:
        return _resolve_path(self.app.upload_dir)

    @property
    def OUTPUT_DIR(self) -> Path:
        return _resolve_path(self.app.output_dir)

    @property
    def DATABASE_PATH(self) -> Path:
        return _resolve_path(self.database.sqlite.path)

    @property
    def STORAGE_BASE_DIR(self) -> Path:
        return _resolve_path(self.storage.local.base_dir)

    @property
    def STORAGE_PUBLIC_BASE_URL(self) -> str:
        return self.storage.local.public_base_url.rstrip("/")

    def ensure_dirs(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def _load_yaml_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    loaded = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml root must be a mapping")
    return loaded


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    payload = {**data}
    payload.setdefault("providers", {})
    jimeng_cfg = dict(payload["providers"].get("jimeng", {}))
    if os.getenv("JIMENG_ENABLED") is not None:
        jimeng_cfg["enabled"] = os.getenv("JIMENG_ENABLED", "false").lower() == "true"
    if os.getenv("JIMENG_APP_KEY"):
        jimeng_cfg["app_key"] = os.getenv("JIMENG_APP_KEY")
    if os.getenv("JIMENG_APP_SECRET"):
        jimeng_cfg["app_secret"] = os.getenv("JIMENG_APP_SECRET")
    if os.getenv("JIMENG_REQ_KEY"):
        jimeng_cfg["req_key"] = os.getenv("JIMENG_REQ_KEY")
    if os.getenv("JIMENG_BASE_URL"):
        jimeng_cfg["base_url"] = os.getenv("JIMENG_BASE_URL")
    if os.getenv("JIMENG_MOCK_MODE") is not None:
        jimeng_cfg["mock_mode"] = os.getenv("JIMENG_MOCK_MODE", "false").lower() == "true"
    payload["providers"]["jimeng"] = jimeng_cfg

    if os.getenv("DATABASE_PATH"):
        payload.setdefault("database", {}).setdefault("sqlite", {})["path"] = os.getenv("DATABASE_PATH")
    if os.getenv("UPLOAD_DIR"):
        payload.setdefault("app", {})["upload_dir"] = os.getenv("UPLOAD_DIR")
    if os.getenv("OUTPUT_DIR"):
        payload.setdefault("app", {})["output_dir"] = os.getenv("OUTPUT_DIR")
    if os.getenv("DATA_DIR"):
        payload.setdefault("app", {})["data_dir"] = os.getenv("DATA_DIR")
    if os.getenv("STORAGE_BASE_DIR"):
        payload.setdefault("storage", {}).setdefault("local", {})["base_dir"] = os.getenv("STORAGE_BASE_DIR")
    if os.getenv("STORAGE_PUBLIC_BASE_URL"):
        payload.setdefault("storage", {}).setdefault("local", {})["public_base_url"] = os.getenv("STORAGE_PUBLIC_BASE_URL")
    return payload


@lru_cache()
def get_settings() -> AppConfig:
    data = _apply_env_overrides(_load_yaml_config())
    settings = AppConfig.model_validate(data)
    settings.ensure_dirs()
    return settings
