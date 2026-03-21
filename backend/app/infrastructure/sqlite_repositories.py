from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from ..domain.models import CharacterImageAssistantConfig, ProviderConfig, RenderJob, SceneJob, StoryAssistantConfig


def _now() -> float:
    return time.time()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class SqliteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def transaction(self):
        return self._lock, self.connect()

    def _init_db(self) -> None:
        with self._lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS render_jobs (
                    job_id TEXT PRIMARY KEY,
                    backend TEXT NOT NULL,
                    provider_code TEXT NOT NULL,
                    provider_config_snapshot_json TEXT,
                    prompt TEXT,
                    storyboard_json TEXT NOT NULL,
                    images_json TEXT NOT NULL,
                    bgm_path TEXT,
                    output_path TEXT,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status_text TEXT,
                    effective_backend TEXT,
                    effective_provider TEXT,
                    fallback_reason TEXT,
                    error TEXT,
                    template_id TEXT,
                    template_name TEXT,
                    platform TEXT,
                    final_video_url TEXT,
                    final_cover_url TEXT,
                    scene_count INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scene_jobs (
                    scene_job_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    scene_index INTEGER NOT NULL,
                    provider_code TEXT NOT NULL,
                    provider_config_snapshot_json TEXT,
                    scene_payload_json TEXT NOT NULL,
                    provider_task_id TEXT,
                    provider_request_url TEXT,
                    provider_get_url TEXT,
                    provider_request_payload_json TEXT,
                    provider_response_payload_json TEXT,
                    provider_status TEXT,
                    normalized_status TEXT NOT NULL,
                    result_video_url TEXT,
                    result_cover_url TEXT,
                    error TEXT,
                    last_polled_at REAL,
                    poll_attempts INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES render_jobs(job_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS provider_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_code TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    description TEXT,
                    config_version INTEGER NOT NULL DEFAULT 1,
                    provider_config_json TEXT NOT NULL DEFAULT '{}',
                    is_valid INTEGER NOT NULL DEFAULT 0,
                    last_checked_at REAL,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS story_assistants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assistant_code TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    description TEXT,
                    protocol TEXT NOT NULL DEFAULT 'openai',
                    base_url TEXT NOT NULL DEFAULT '',
                    api_key TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    temperature REAL NOT NULL DEFAULT 0.7,
                    is_valid INTEGER NOT NULL DEFAULT 0,
                    last_checked_at REAL,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS character_image_assistants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assistant_code TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    description TEXT,
                    protocol TEXT NOT NULL DEFAULT 'openai',
                    base_url TEXT NOT NULL DEFAULT '',
                    api_key TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    is_valid INTEGER NOT NULL DEFAULT 0,
                    last_checked_at REAL,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS visual_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    prompt_fragment TEXT,
                    cover_path TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS frame_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    prompt_fragment TEXT,
                    cover_path TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS character_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    prompt_fragment TEXT,
                    image_path TEXT,
                    group_name TEXT NOT NULL DEFAULT '默认分组',
                    is_public INTEGER NOT NULL DEFAULT 1,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS voice_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    tone TEXT,
                    audio_path TEXT,
                    sample_rate INTEGER,
                    duration_ms INTEGER,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS music_assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    author TEXT,
                    genre_tags TEXT,
                    audio_path TEXT,
                    duration_ms INTEGER,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            self._ensure_story_assistant_protocol(conn)
            self._ensure_character_image_assistant_protocol(conn)
            self._ensure_character_asset_group_name(conn)

    def _ensure_character_asset_group_name(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(character_assets)").fetchall()}
        if "group_name" not in columns:
            conn.execute("ALTER TABLE character_assets ADD COLUMN group_name TEXT NOT NULL DEFAULT '默认分组'")
        conn.execute(
            """
            UPDATE character_assets
            SET group_name = '默认分组'
            WHERE group_name IS NULL OR TRIM(group_name) = ''
            """
        )

    def _ensure_story_assistant_protocol(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(story_assistants)").fetchall()}
        if "protocol" not in columns:
            conn.execute("ALTER TABLE story_assistants ADD COLUMN protocol TEXT NOT NULL DEFAULT 'openai'")
        conn.execute(
            """
            UPDATE story_assistants
            SET protocol = 'openai'
            WHERE protocol IS NULL OR TRIM(protocol) = ''
            """
        )

    def _ensure_character_image_assistant_protocol(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(character_image_assistants)").fetchall()}
        if "protocol" not in columns:
            conn.execute("ALTER TABLE character_image_assistants ADD COLUMN protocol TEXT NOT NULL DEFAULT 'openai'")
        conn.execute(
            """
            UPDATE character_image_assistants
            SET protocol = 'openai'
            WHERE protocol IS NULL OR TRIM(protocol) = ''
            """
        )


class SqliteProviderConfigRepository:
    def __init__(self, db: SqliteDatabase) -> None:
        self.db = db

    def _serialize(self, row: sqlite3.Row) -> ProviderConfig:
        return ProviderConfig(
            id=row["id"],
            provider_code=row["provider_code"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            sort_order=row["sort_order"],
            description=row["description"] or "",
            config_version=row["config_version"],
            provider_config_json=_json_loads(row["provider_config_json"], {}),
            is_valid=bool(row["is_valid"]),
            last_checked_at=row["last_checked_at"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_all(self) -> list[ProviderConfig]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM provider_configs ORDER BY sort_order ASC, provider_code ASC").fetchall()
            return [self._serialize(row) for row in rows]

    def get(self, provider_code: str) -> ProviderConfig | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM provider_configs WHERE provider_code = ?", (provider_code,)).fetchone()
            return self._serialize(row) if row else None

    def upsert(self, config: ProviderConfig) -> ProviderConfig:
        now = _now()
        with self.db._lock, self.db.connect() as conn:
            exists = conn.execute("SELECT id FROM provider_configs WHERE provider_code = ?", (config.provider_code,)).fetchone()
            if exists is None:
                conn.execute(
                    """
                    INSERT INTO provider_configs (
                      provider_code, display_name, enabled, sort_order, description, config_version,
                      provider_config_json, is_valid, last_checked_at, last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        config.provider_code,
                        config.display_name,
                        1 if config.enabled else 0,
                        config.sort_order,
                        config.description,
                        config.config_version,
                        _json_dumps(config.provider_config_json),
                        1 if config.is_valid else 0,
                        config.last_checked_at or now,
                        config.last_error,
                        config.created_at or now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE provider_configs
                    SET display_name = ?, enabled = ?, sort_order = ?, description = ?, config_version = ?,
                        provider_config_json = ?, is_valid = ?, last_checked_at = ?, last_error = ?, updated_at = ?
                    WHERE provider_code = ?
                    """,
                    (
                        config.display_name,
                        1 if config.enabled else 0,
                        config.sort_order,
                        config.description,
                        config.config_version,
                        _json_dumps(config.provider_config_json),
                        1 if config.is_valid else 0,
                        config.last_checked_at or now,
                        config.last_error,
                        now,
                        config.provider_code,
                    ),
                )
            row = conn.execute("SELECT * FROM provider_configs WHERE provider_code = ?", (config.provider_code,)).fetchone()
            return self._serialize(row)

    def seed(self, config: ProviderConfig) -> None:
        current = self.get(config.provider_code)
        if current and current.provider_config_json:
            return
        self.upsert(config)


class SqliteStoryAssistantConfigRepository:
    def __init__(self, db: SqliteDatabase) -> None:
        self.db = db

    def _serialize(self, row: sqlite3.Row) -> StoryAssistantConfig:
        return StoryAssistantConfig(
            id=row["id"],
            assistant_code=row["assistant_code"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            sort_order=row["sort_order"],
            description=row["description"] or "",
            protocol=row["protocol"] or "openai",
            base_url=row["base_url"] or "",
            api_key=row["api_key"] or "",
            model=row["model"] or "",
            system_prompt=row["system_prompt"] or "",
            temperature=float(row["temperature"] or 0.7),
            is_valid=bool(row["is_valid"]),
            last_checked_at=row["last_checked_at"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_all(self) -> list[StoryAssistantConfig]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM story_assistants ORDER BY sort_order ASC, display_name ASC").fetchall()
            return [self._serialize(row) for row in rows]

    def get(self, assistant_code: str) -> StoryAssistantConfig | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM story_assistants WHERE assistant_code = ?", (assistant_code,)).fetchone()
            return self._serialize(row) if row else None

    def upsert(self, config: StoryAssistantConfig) -> StoryAssistantConfig:
        now = _now()
        with self.db._lock, self.db.connect() as conn:
            exists = conn.execute("SELECT id FROM story_assistants WHERE assistant_code = ?", (config.assistant_code,)).fetchone()
            values = (
                config.assistant_code,
                config.display_name,
                1 if config.enabled else 0,
                config.sort_order,
                config.description,
                config.protocol,
                config.base_url,
                config.api_key,
                config.model,
                config.system_prompt,
                float(config.temperature),
                1 if config.is_valid else 0,
                config.last_checked_at or now,
                config.last_error,
            )
            if exists is None:
                conn.execute(
                    """
                    INSERT INTO story_assistants (
                      assistant_code, display_name, enabled, sort_order, description, protocol, base_url,
                      api_key, model, system_prompt, temperature, is_valid, last_checked_at,
                      last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values + (config.created_at or now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE story_assistants
                    SET display_name = ?, enabled = ?, sort_order = ?, description = ?, protocol = ?, base_url = ?,
                        api_key = ?, model = ?, system_prompt = ?, temperature = ?, is_valid = ?,
                        last_checked_at = ?, last_error = ?, updated_at = ?
                    WHERE assistant_code = ?
                    """,
                    (
                        config.display_name,
                        1 if config.enabled else 0,
                        config.sort_order,
                        config.description,
                        config.protocol,
                        config.base_url,
                        config.api_key,
                        config.model,
                        config.system_prompt,
                        float(config.temperature),
                        1 if config.is_valid else 0,
                        config.last_checked_at or now,
                        config.last_error,
                        now,
                        config.assistant_code,
                    ),
                )
            row = conn.execute("SELECT * FROM story_assistants WHERE assistant_code = ?", (config.assistant_code,)).fetchone()
            return self._serialize(row)

    def seed(self, config: StoryAssistantConfig) -> None:
        current = self.get(config.assistant_code)
        if current and (current.base_url or current.model or current.api_key):
            return
        self.upsert(config)


class SqliteCharacterImageAssistantConfigRepository:
    def __init__(self, db: SqliteDatabase) -> None:
        self.db = db

    def _serialize(self, row: sqlite3.Row) -> CharacterImageAssistantConfig:
        return CharacterImageAssistantConfig(
            id=row["id"],
            assistant_code=row["assistant_code"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            sort_order=row["sort_order"],
            description=row["description"] or "",
            protocol=row["protocol"] or "openai",
            base_url=row["base_url"] or "",
            api_key=row["api_key"] or "",
            model=row["model"] or "",
            system_prompt=row["system_prompt"] or "",
            is_valid=bool(row["is_valid"]),
            last_checked_at=row["last_checked_at"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_all(self) -> list[CharacterImageAssistantConfig]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM character_image_assistants ORDER BY sort_order ASC, display_name ASC").fetchall()
            return [self._serialize(row) for row in rows]

    def get(self, assistant_code: str) -> CharacterImageAssistantConfig | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM character_image_assistants WHERE assistant_code = ?", (assistant_code,)).fetchone()
            return self._serialize(row) if row else None

    def upsert(self, config: CharacterImageAssistantConfig) -> CharacterImageAssistantConfig:
        now = _now()
        with self.db._lock, self.db.connect() as conn:
            exists = conn.execute(
                "SELECT id FROM character_image_assistants WHERE assistant_code = ?",
                (config.assistant_code,),
            ).fetchone()
            values = (
                config.assistant_code,
                config.display_name,
                1 if config.enabled else 0,
                config.sort_order,
                config.description,
                config.protocol,
                config.base_url,
                config.api_key,
                config.model,
                config.system_prompt,
                1 if config.is_valid else 0,
                config.last_checked_at or now,
                config.last_error,
            )
            if exists is None:
                conn.execute(
                    """
                    INSERT INTO character_image_assistants (
                      assistant_code, display_name, enabled, sort_order, description, protocol, base_url,
                      api_key, model, system_prompt, is_valid, last_checked_at, last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values + (config.created_at or now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE character_image_assistants
                    SET display_name = ?, enabled = ?, sort_order = ?, description = ?, protocol = ?, base_url = ?,
                        api_key = ?, model = ?, system_prompt = ?, is_valid = ?, last_checked_at = ?, last_error = ?, updated_at = ?
                    WHERE assistant_code = ?
                    """,
                    (
                        config.display_name,
                        1 if config.enabled else 0,
                        config.sort_order,
                        config.description,
                        config.protocol,
                        config.base_url,
                        config.api_key,
                        config.model,
                        config.system_prompt,
                        1 if config.is_valid else 0,
                        config.last_checked_at or now,
                        config.last_error,
                        now,
                        config.assistant_code,
                    ),
                )
            row = conn.execute(
                "SELECT * FROM character_image_assistants WHERE assistant_code = ?",
                (config.assistant_code,),
            ).fetchone()
            return self._serialize(row)

    def seed(self, config: CharacterImageAssistantConfig) -> None:
        current = self.get(config.assistant_code)
        if current and (current.base_url or current.model or current.api_key):
            return
        self.upsert(config)


class SqliteAssetRepository:
    TABLES = {
        "visuals": "visual_assets",
        "frames": "frame_assets",
        "characters": "character_assets",
        "voices": "voice_assets",
        "music": "music_assets",
    }

    def __init__(self, db: SqliteDatabase, public_base_url: str = "/media") -> None:
        self.db = db
        self.public_base_url = public_base_url.rstrip("/")

    def _table(self, asset_type: str) -> str:
        if asset_type not in self.TABLES:
            raise ValueError(f"unknown asset type: {asset_type}")
        return self.TABLES[asset_type]

    def _normalize(self, asset_type: str, payload: dict[str, Any], *, existing_id: str | None = None) -> dict[str, Any]:
        now = _now()
        normalized = {
            "id": existing_id or payload.get("id") or f"{asset_type[:-1]}-{uuid.uuid4().hex[:8]}",
            "name": str(payload.get("name") or "").strip(),
            "description": str(payload.get("description") or "").strip(),
            "path": str(payload.get("path") or "").strip(),
            "mime_type": str(payload.get("mime_type") or "application/octet-stream").strip(),
            "size_bytes": int(payload.get("size_bytes") or 0),
            "enabled": 1 if bool(payload.get("enabled", True)) else 0,
            "sort_order": int(payload.get("sort_order") or 100),
            "created_at": float(payload.get("created_at") or now),
            "updated_at": now,
        }
        if not normalized["name"]:
            raise ValueError("name is required")
        if not normalized["path"]:
            raise ValueError("asset file path is required")
        if asset_type in {"visuals", "frames"}:
            normalized["prompt_fragment"] = str(payload.get("prompt_fragment") or "").strip()
            normalized["cover_path"] = str(payload.get("cover_path") or normalized["path"]).strip()
        elif asset_type == "characters":
            normalized["prompt_fragment"] = str(payload.get("prompt_fragment") or "").strip()
            normalized["image_path"] = str(payload.get("image_path") or normalized["path"]).strip()
            normalized["group_name"] = str(payload.get("group_name") or "默认分组").strip() or "默认分组"
            normalized["is_public"] = 1 if bool(payload.get("is_public", True)) else 0
        elif asset_type == "voices":
            normalized["tone"] = str(payload.get("tone") or "").strip()
            normalized["audio_path"] = str(payload.get("audio_path") or normalized["path"]).strip()
            normalized["sample_rate"] = _to_int_or_none(payload.get("sample_rate"))
            normalized["duration_ms"] = _to_int_or_none(payload.get("duration_ms"))
        elif asset_type == "music":
            normalized["author"] = str(payload.get("author") or "").strip()
            normalized["genre_tags"] = str(payload.get("genre_tags") or "").strip()
            normalized["audio_path"] = str(payload.get("audio_path") or normalized["path"]).strip()
            normalized["duration_ms"] = _to_int_or_none(payload.get("duration_ms"))
        return normalized

    def _columns(self, asset_type: str) -> list[str]:
        common = ["id", "name", "description", "path", "mime_type", "size_bytes", "enabled", "sort_order", "created_at", "updated_at"]
        if asset_type in {"visuals", "frames"}:
            return common[:6] + ["prompt_fragment", "cover_path"] + common[6:]
        if asset_type == "characters":
            return common[:6] + ["prompt_fragment", "image_path", "group_name", "is_public"] + common[6:]
        if asset_type == "voices":
            return common[:6] + ["tone", "audio_path", "sample_rate", "duration_ms"] + common[6:]
        return common[:6] + ["author", "genre_tags", "audio_path", "duration_ms"] + common[6:]

    def _serialize(self, asset_type: str, row: sqlite3.Row) -> dict[str, Any]:
        base = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "path": row["path"],
            "mime_type": row["mime_type"],
            "size_bytes": row["size_bytes"],
            "enabled": bool(row["enabled"]),
            "sort_order": row["sort_order"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "public_url": f"{self.public_base_url}/{str(row['path']).lstrip('/')}",
        }
        if asset_type in {"visuals", "frames"}:
            base.update(
                prompt_fragment=row["prompt_fragment"],
                cover_path=row["cover_path"],
                cover_url=f"{self.public_base_url}/{str(row['cover_path'] or row['path']).lstrip('/')}",
            )
        elif asset_type == "characters":
            base.update(
                prompt_fragment=row["prompt_fragment"],
                image_path=row["image_path"],
                image_url=f"{self.public_base_url}/{str(row['image_path'] or row['path']).lstrip('/')}",
                group_name=(row["group_name"] or "默认分组"),
            )
        elif asset_type == "voices":
            base.update(
                tone=row["tone"],
                audio_path=row["audio_path"],
                audio_url=f"{self.public_base_url}/{str(row['audio_path'] or row['path']).lstrip('/')}",
                sample_rate=row["sample_rate"],
                duration_ms=row["duration_ms"],
            )
        elif asset_type == "music":
            base.update(
                author=row["author"],
                genre_tags=row["genre_tags"],
                audio_path=row["audio_path"],
                audio_url=f"{self.public_base_url}/{str(row['audio_path'] or row['path']).lstrip('/')}",
                duration_ms=row["duration_ms"],
            )
        return base

    def list_assets(self, asset_type: str, enabled_only: bool = True) -> list[dict[str, Any]]:
        table = self._table(asset_type)
        with self.db._lock, self.db.connect() as conn:
            query = f"SELECT * FROM {table}"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY sort_order ASC, name ASC"
            rows = conn.execute(query).fetchall()
            return [self._serialize(asset_type, row) for row in rows]

    def list_grouped(self, enabled_only: bool = True) -> dict[str, list[dict[str, Any]]]:
        return {asset_type: self.list_assets(asset_type, enabled_only=enabled_only) for asset_type in self.TABLES}

    def get_asset(self, asset_type: str, asset_id: str) -> dict[str, Any] | None:
        table = self._table(asset_type)
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (asset_id,)).fetchone()
            return self._serialize(asset_type, row) if row else None

    def create_asset(self, asset_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize(asset_type, payload)
        columns = self._columns(asset_type)
        with self.db._lock, self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO {self._table(asset_type)} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                tuple(normalized.get(column) for column in columns),
            )
            row = conn.execute(f"SELECT * FROM {self._table(asset_type)} WHERE id = ?", (normalized["id"],)).fetchone()
            return self._serialize(asset_type, row)

    def update_asset(self, asset_type: str, asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        table = self._table(asset_type)
        with self.db._lock, self.db.connect() as conn:
            existing = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (asset_id,)).fetchone()
            if existing is None:
                raise KeyError(asset_id)
            merged = {**dict(existing), **payload}
            normalized = self._normalize(asset_type, merged, existing_id=asset_id)
            columns = [col for col in self._columns(asset_type) if col not in {"id", "created_at"}]
            conn.execute(
                f"UPDATE {table} SET {', '.join(f'{col} = ?' for col in columns)} WHERE id = ?",
                tuple(normalized.get(col) for col in columns) + (asset_id,),
            )
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (asset_id,)).fetchone()
            return self._serialize(asset_type, row)

    def delete_asset(self, asset_type: str, asset_id: str) -> dict[str, Any] | None:
        table = self._table(asset_type)
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (asset_id,)).fetchone()
            if row is None:
                return None
            payload = self._serialize(asset_type, row)
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (asset_id,))
            return payload


class SqliteSceneJobRepository:
    def __init__(self, db: SqliteDatabase) -> None:
        self.db = db

    def _serialize(self, row: sqlite3.Row) -> SceneJob:
        return SceneJob(
            scene_job_id=row["scene_job_id"],
            job_id=row["job_id"],
            scene_index=row["scene_index"],
            provider_code=row["provider_code"],
            provider_config_snapshot_json=_json_loads(row["provider_config_snapshot_json"], {}),
            scene_payload=_json_loads(row["scene_payload_json"], {}),
            provider_task_id=row["provider_task_id"],
            provider_request_url=row["provider_request_url"],
            provider_get_url=row["provider_get_url"],
            provider_request_payload_json=_json_loads(row["provider_request_payload_json"], {}),
            provider_response_payload_json=_json_loads(row["provider_response_payload_json"], {}),
            provider_status=row["provider_status"],
            normalized_status=row["normalized_status"],
            result_video_url=row["result_video_url"],
            result_cover_url=row["result_cover_url"],
            error=row["error"],
            last_polled_at=row["last_polled_at"],
            poll_attempts=row["poll_attempts"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_many(self, scene_jobs: list[SceneJob]) -> None:
        if not scene_jobs:
            return
        with self.db._lock, self.db.connect() as conn:
            for scene in scene_jobs:
                conn.execute(
                    """
                    INSERT INTO scene_jobs (
                      scene_job_id, job_id, scene_index, provider_code, provider_config_snapshot_json,
                      scene_payload_json, provider_task_id, provider_request_url, provider_get_url,
                      provider_request_payload_json, provider_response_payload_json, provider_status,
                      normalized_status, result_video_url, result_cover_url, error, last_polled_at,
                      poll_attempts, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scene.scene_job_id,
                        scene.job_id,
                        scene.scene_index,
                        scene.provider_code,
                        _json_dumps(scene.provider_config_snapshot_json),
                        _json_dumps(scene.scene_payload),
                        scene.provider_task_id,
                        scene.provider_request_url,
                        scene.provider_get_url,
                        _json_dumps(scene.provider_request_payload_json),
                        _json_dumps(scene.provider_response_payload_json),
                        scene.provider_status,
                        scene.normalized_status,
                        scene.result_video_url,
                        scene.result_cover_url,
                        scene.error,
                        scene.last_polled_at,
                        scene.poll_attempts,
                        scene.created_at,
                        scene.updated_at,
                    ),
                )

    def get(self, scene_job_id: str) -> SceneJob | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM scene_jobs WHERE scene_job_id = ?", (scene_job_id,)).fetchone()
            return self._serialize(row) if row else None

    def list_for_job(self, job_id: str) -> list[SceneJob]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM scene_jobs WHERE job_id = ? ORDER BY scene_index ASC", (job_id,)).fetchall()
            return [self._serialize(row) for row in rows]

    def list_by_status(self, statuses: list[str], limit: int = 20) -> list[SceneJob]:
        if not statuses:
            return []
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM scene_jobs WHERE normalized_status IN ({', '.join('?' for _ in statuses)}) ORDER BY updated_at ASC LIMIT ?",
                (*statuses, limit),
            ).fetchall()
            return [self._serialize(row) for row in rows]

    def patch(self, scene_job_id: str, **fields: Any) -> None:
        if not fields:
            return
        for key in ("provider_config_snapshot_json", "scene_payload_json", "provider_request_payload_json", "provider_response_payload_json"):
            if key in fields and not isinstance(fields[key], str):
                fields[key] = _json_dumps(fields[key])
        fields["updated_at"] = _now()
        with self.db._lock, self.db.connect() as conn:
            conn.execute(
                f"UPDATE scene_jobs SET {', '.join(f'{k} = ?' for k in fields)} WHERE scene_job_id = ?",
                (*fields.values(), scene_job_id),
            )


class SqliteRenderJobRepository:
    def __init__(self, db: SqliteDatabase, scene_repo: SqliteSceneJobRepository) -> None:
        self.db = db
        self.scene_repo = scene_repo

    def _scene_status_counts(self, conn: sqlite3.Connection, job_id: str) -> dict[str, int]:
        rows = conn.execute("SELECT normalized_status, COUNT(*) AS count FROM scene_jobs WHERE job_id = ? GROUP BY normalized_status", (job_id,)).fetchall()
        return {row["normalized_status"]: int(row["count"]) for row in rows}

    def _serialize(self, conn: sqlite3.Connection, row: sqlite3.Row, include_scenes: bool) -> RenderJob:
        scene_jobs = self.scene_repo.list_for_job(row["job_id"]) if include_scenes else []
        return RenderJob(
            job_id=row["job_id"],
            backend=row["backend"],
            provider_code=row["provider_code"],
            provider_config_snapshot_json=_json_loads(row["provider_config_snapshot_json"], {}),
            prompt=row["prompt"] or "",
            storyboard=_json_loads(row["storyboard_json"], {}),
            images=_json_loads(row["images_json"], []),
            bgm_path=row["bgm_path"],
            output_path=row["output_path"],
            status=row["status"],
            stage=row["stage"],
            status_text=row["status_text"] or "",
            effective_backend=row["effective_backend"],
            effective_provider=row["effective_provider"],
            fallback_reason=row["fallback_reason"],
            error=row["error"],
            template_id=row["template_id"],
            template_name=row["template_name"],
            platform=row["platform"],
            final_video_url=row["final_video_url"],
            final_cover_url=row["final_cover_url"],
            scene_count=row["scene_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            scene_status_counts=self._scene_status_counts(conn, row["job_id"]),
            scene_jobs=scene_jobs,
        )

    def create(self, job: RenderJob) -> None:
        with self.db._lock, self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO render_jobs (
                  job_id, backend, provider_code, provider_config_snapshot_json, prompt, storyboard_json,
                  images_json, bgm_path, output_path, status, stage, status_text, effective_backend,
                  effective_provider, fallback_reason, error, template_id, template_name, platform,
                  final_video_url, final_cover_url, scene_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.backend,
                    job.provider_code,
                    _json_dumps(job.provider_config_snapshot_json),
                    job.prompt,
                    _json_dumps(job.storyboard),
                    _json_dumps(job.images),
                    job.bgm_path,
                    job.output_path,
                    job.status,
                    job.stage,
                    job.status_text,
                    job.effective_backend,
                    job.effective_provider,
                    job.fallback_reason,
                    job.error,
                    job.template_id,
                    job.template_name,
                    job.platform,
                    job.final_video_url,
                    job.final_cover_url,
                    job.scene_count,
                    job.created_at,
                    job.updated_at,
                ),
            )

    def get(self, job_id: str) -> RenderJob | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._serialize(conn, row, True) if row else None

    def list_recent(self, limit: int = 30) -> list[RenderJob]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM render_jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [self._serialize(conn, row, False) for row in rows]

    def patch(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = _now()
        with self.db._lock, self.db.connect() as conn:
            conn.execute(f"UPDATE render_jobs SET {', '.join(f'{k} = ?' for k in fields)} WHERE job_id = ?", (*fields.values(), job_id))

    def delete(self, job_id: str) -> RenderJob | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            payload = self._serialize(conn, row, True)
            conn.execute("DELETE FROM render_jobs WHERE job_id = ?", (job_id,))
            return payload

    def list_ready_for_composition(self, limit: int = 10) -> list[RenderJob]:
        with self.db._lock, self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM render_jobs WHERE status IN ('running', 'submitted', 'queued', 'composing') ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
            ready: list[RenderJob] = []
            for row in rows:
                counts = self._scene_status_counts(conn, row["job_id"])
                scene_count = int(row["scene_count"] or 0)
                if scene_count and counts.get("succeeded", 0) == scene_count:
                    ready.append(self._serialize(conn, row, True))
            return ready

    def refresh_status(self, job_id: str) -> RenderJob | None:
        with self.db._lock, self.db.connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            counts = self._scene_status_counts(conn, job_id)
            scene_count = int(row["scene_count"] or 0)
            if row["error"]:
                status, stage, status_text = "failed", "failed", row["error"]
            elif row["final_video_url"]:
                status, stage, status_text = "done", "done", "视频已合成完成"
            elif counts.get("failed", 0) > 0:
                status, stage, status_text = "failed", "failed", "至少一个分镜生成失败"
            elif scene_count and counts.get("succeeded", 0) == scene_count:
                status, stage, status_text = "composing", "composing", "所有分镜已完成，等待最终合成"
            elif counts.get("running", 0) > 0:
                status, stage, status_text = "running", "rendering", "分镜任务生成中"
            elif counts.get("submitted", 0) > 0:
                status, stage, status_text = "submitted", "submitted", "分镜任务已提交，等待厂商执行"
            else:
                status, stage, status_text = "queued", "queued", "等待提交分镜任务"
            conn.execute(
                "UPDATE render_jobs SET status = ?, stage = ?, status_text = ?, updated_at = ? WHERE job_id = ?",
                (status, stage, status_text, _now(), job_id),
            )
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._serialize(conn, row, True)
