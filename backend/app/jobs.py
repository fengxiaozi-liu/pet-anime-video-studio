from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


@dataclass
class JobStore:
    path: Path
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_legacy_json()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
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
                """
            )

    def _legacy_json_path(self) -> Path:
        if self.path.suffix == ".json":
            return self.path
        return self.path.with_name("jobs.json")

    def _migrate_legacy_json(self) -> None:
        legacy = self._legacy_json_path()
        if not legacy.exists() or legacy == self.path:
            return

        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT COUNT(*) AS count FROM render_jobs").fetchone()["count"]
            if existing:
                return

            try:
                data = json.loads(legacy.read_text("utf-8"))
            except Exception:
                return

            for job_id, job in data.items():
                storyboard = job.get("storyboard") or {}
                images = job.get("images") or []
                created_at = float(job.get("created_at") or _now())
                updated_at = float(job.get("updated_at") or created_at)
                provider_code = "jimeng"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO render_jobs (
                        job_id, backend, provider_code, provider_config_snapshot_json, prompt, storyboard_json,
                        images_json, bgm_path, output_path, status, stage, status_text, effective_backend,
                        effective_provider, fallback_reason, error, template_id, template_name, platform,
                        final_video_url, final_cover_url, scene_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        job.get("backend") or "cloud",
                        provider_code,
                        _json_dumps({}),
                        job.get("prompt") or "",
                        _json_dumps(storyboard),
                        _json_dumps(images),
                        job.get("bgm"),
                        job.get("output"),
                        job.get("status") or "queued",
                        job.get("stage") or "queued",
                        job.get("status_text") or "",
                        job.get("effective_backend"),
                        job.get("effective_provider"),
                        job.get("fallback_reason"),
                        job.get("error"),
                        job.get("template_id"),
                        job.get("template_name"),
                        job.get("platform"),
                        job.get("output") if job.get("status") == "done" else None,
                        None,
                        len(storyboard.get("scenes") or []),
                        created_at,
                        updated_at,
                    ),
                )

                for index, scene in enumerate(storyboard.get("scenes") or []):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO scene_jobs (
                            scene_job_id, job_id, scene_index, provider_code, provider_config_snapshot_json,
                            scene_payload_json, normalized_status, created_at, updated_at, result_video_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{job_id}:scene:{index}",
                            job_id,
                            index,
                            provider_code,
                            _json_dumps({}),
                            _json_dumps(scene),
                            "succeeded" if job.get("status") == "done" else "queued",
                            created_at,
                            updated_at,
                            job.get("output") if job.get("status") == "done" and index == 0 else None,
                        ),
                    )

    def seed_provider_config(
        self,
        *,
        provider_code: str,
        display_name: str,
        description: str,
        sort_order: int,
        provider_config_json: dict[str, Any],
        enabled: bool,
        is_valid: bool,
        last_error: str | None,
    ) -> None:
        now = _now()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT provider_code, provider_config_json, enabled, is_valid FROM provider_configs WHERE provider_code = ?",
                (provider_code,),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO provider_configs (
                        provider_code, display_name, enabled, sort_order, description, config_version,
                        provider_config_json, is_valid, last_checked_at, last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        provider_code,
                        display_name,
                        1 if enabled else 0,
                        sort_order,
                        description,
                        _json_dumps(provider_config_json),
                        1 if is_valid else 0,
                        now,
                        last_error,
                        now,
                        now,
                    ),
                )
                return

            current_config = _json_loads(row["provider_config_json"], {})
            if current_config:
                return

            conn.execute(
                """
                UPDATE provider_configs
                SET display_name = ?, enabled = ?, sort_order = ?, description = ?, provider_config_json = ?,
                    is_valid = ?, last_checked_at = ?, last_error = ?, updated_at = ?
                WHERE provider_code = ?
                """,
                (
                    display_name,
                    1 if enabled else 0,
                    sort_order,
                    description,
                    _json_dumps(provider_config_json),
                    1 if is_valid else 0,
                    now,
                    last_error,
                    now,
                    provider_code,
                ),
            )

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
        now = _now()
        scenes = list(storyboard.get("scenes") or [])
        provider_snapshot = self.get_provider_config(provider) or {}
        provider_config = provider_snapshot.get("provider_config_json") or {}
        with self._lock, self._connect() as conn:
            exists = conn.execute("SELECT job_id FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if exists:
                raise ValueError("job exists")

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
                    job_id,
                    backend,
                    provider,
                    _json_dumps(provider_config),
                    prompt,
                    _json_dumps(storyboard),
                    _json_dumps(images),
                    bgm,
                    output,
                    "queued",
                    "queued",
                    "任务已创建，等待分镜任务提交",
                    extra_fields.get("requested_backend", backend),
                    None,
                    None,
                    None,
                    extra_fields.get("template_id"),
                    extra_fields.get("template_name"),
                    extra_fields.get("platform"),
                    None,
                    None,
                    len(scenes),
                    now,
                    now,
                ),
            )

            for index, scene in enumerate(scenes):
                conn.execute(
                    """
                    INSERT INTO scene_jobs (
                        scene_job_id, job_id, scene_index, provider_code, provider_config_snapshot_json,
                        scene_payload_json, provider_task_id, provider_request_url, provider_get_url,
                        provider_request_payload_json, provider_response_payload_json, provider_status,
                        normalized_status, result_video_url, result_cover_url, error, last_polled_at,
                        poll_attempts, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL, NULL, 0, ?, ?)
                    """,
                    (
                        f"{job_id}:scene:{index}",
                        job_id,
                        index,
                        provider,
                        _json_dumps(provider_config),
                        _json_dumps(scene),
                        now,
                        now,
                    ),
                )

    def _serialize_scene_job(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "scene_job_id": row["scene_job_id"],
            "job_id": row["job_id"],
            "scene_index": row["scene_index"],
            "provider_code": row["provider_code"],
            "provider_config_snapshot_json": _json_loads(row["provider_config_snapshot_json"], {}),
            "scene_payload": _json_loads(row["scene_payload_json"], {}),
            "provider_task_id": row["provider_task_id"],
            "provider_request_url": row["provider_request_url"],
            "provider_get_url": row["provider_get_url"],
            "provider_request_payload_json": _json_loads(row["provider_request_payload_json"], {}),
            "provider_response_payload_json": _json_loads(row["provider_response_payload_json"], {}),
            "provider_status": row["provider_status"],
            "normalized_status": row["normalized_status"],
            "result_video_url": row["result_video_url"],
            "result_cover_url": row["result_cover_url"],
            "error": row["error"],
            "last_polled_at": row["last_polled_at"],
            "poll_attempts": row["poll_attempts"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _scene_status_counts(self, conn: sqlite3.Connection, job_id: str) -> dict[str, int]:
        rows = conn.execute(
            "SELECT normalized_status, COUNT(*) AS count FROM scene_jobs WHERE job_id = ? GROUP BY normalized_status",
            (job_id,),
        ).fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["normalized_status"]] = int(row["count"])
        return counts

    def _serialize_render_job(self, conn: sqlite3.Connection, row: sqlite3.Row, include_scenes: bool) -> dict[str, Any]:
        job_id = row["job_id"]
        storyboard = _json_loads(row["storyboard_json"], {})
        images = _json_loads(row["images_json"], [])
        counts = self._scene_status_counts(conn, job_id)
        scenes = []
        if include_scenes:
            scenes = [
                self._serialize_scene_job(scene_row)
                for scene_row in conn.execute(
                    "SELECT * FROM scene_jobs WHERE job_id = ? ORDER BY scene_index ASC",
                    (job_id,),
                ).fetchall()
            ]

        return {
            "job_id": job_id,
            "backend": row["backend"],
            "provider": row["provider_code"],
            "provider_code": row["provider_code"],
            "prompt": row["prompt"],
            "storyboard": storyboard,
            "images": images,
            "bgm": row["bgm_path"],
            "output": row["output_path"],
            "status": row["status"],
            "stage": row["stage"],
            "status_text": row["status_text"],
            "effective_backend": row["effective_backend"],
            "effective_provider": row["effective_provider"],
            "fallback_reason": row["fallback_reason"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "template_id": row["template_id"],
            "template_name": row["template_name"],
            "platform": row["platform"],
            "final_video_url": row["final_video_url"],
            "final_cover_url": row["final_cover_url"],
            "scene_count": row["scene_count"],
            "provider_config_snapshot_json": _json_loads(row["provider_config_snapshot_json"], {}),
            "scene_status_counts": counts,
            "scene_jobs": scenes,
        }

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            return self._serialize_render_job(conn, row, include_scenes=True)

    def get_render_job_row(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            return dict(row)

    def list_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM render_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._serialize_render_job(conn, row, include_scenes=False) for row in rows]

    def patch(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = _now()
        self._patch_row("render_jobs", "job_id", job_id, fields)

    def patch_scene_job(self, scene_job_id: str, **fields: Any) -> None:
        if not fields:
            return
        for key in (
            "provider_config_snapshot_json",
            "scene_payload_json",
            "provider_request_payload_json",
            "provider_response_payload_json",
        ):
            if key in fields and not isinstance(fields[key], str):
                fields[key] = _json_dumps(fields[key])
        fields["updated_at"] = _now()
        self._patch_row("scene_jobs", "scene_job_id", scene_job_id, fields)

    def _patch_row(self, table: str, key_field: str, key_value: str, fields: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            exists = conn.execute(f"SELECT {key_field} FROM {table} WHERE {key_field} = ?", (key_value,)).fetchone()
            if exists is None:
                raise KeyError(key_value)
            columns = ", ".join(f"{field} = ?" for field in fields)
            values = list(fields.values()) + [key_value]
            conn.execute(f"UPDATE {table} SET {columns} WHERE {key_field} = ?", values)

    def get_scene_job(self, scene_job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM scene_jobs WHERE scene_job_id = ?", (scene_job_id,)).fetchone()
            if row is None:
                return None
            return self._serialize_scene_job(row)

    def list_scene_jobs(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM scene_jobs WHERE job_id = ? ORDER BY scene_index ASC",
                (job_id,),
            ).fetchall()
            return [self._serialize_scene_job(row) for row in rows]

    def list_scene_jobs_by_status(self, statuses: list[str], limit: int = 20) -> list[dict[str, Any]]:
        if not statuses:
            return []
        placeholders = ", ".join("?" for _ in statuses)
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM scene_jobs
                WHERE normalized_status IN ({placeholders})
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (*statuses, limit),
            ).fetchall()
            return [self._serialize_scene_job(row) for row in rows]

    def list_jobs_ready_for_composition(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM render_jobs
                WHERE status IN ('running', 'submitted', 'queued', 'composing')
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ready: list[dict[str, Any]] = []
            for row in rows:
                counts = self._scene_status_counts(conn, row["job_id"])
                scene_count = int(row["scene_count"] or 0)
                if scene_count and counts.get("succeeded", 0) == scene_count:
                    ready.append(self._serialize_render_job(conn, row, include_scenes=True))
            return ready

    def refresh_render_job_status(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            counts = self._scene_status_counts(conn, job_id)
            scene_count = int(row["scene_count"] or 0)
            final_video_url = row["final_video_url"]

            status = row["status"]
            stage = row["stage"]
            status_text = row["status_text"]

            if row["error"]:
                status = "failed"
                stage = "failed"
                status_text = row["error"]
            elif final_video_url:
                status = "done"
                stage = "done"
                status_text = "视频已合成完成"
            elif counts.get("failed", 0) > 0:
                status = "failed"
                stage = "failed"
                status_text = "至少一个分镜生成失败"
            elif scene_count and counts.get("succeeded", 0) == scene_count:
                status = "composing"
                stage = "composing"
                status_text = "所有分镜已完成，等待最终合成"
            elif counts.get("running", 0) > 0:
                status = "running"
                stage = "rendering"
                status_text = "分镜任务生成中"
            elif counts.get("submitted", 0) > 0:
                status = "submitted"
                stage = "submitted"
                status_text = "分镜任务已提交，等待厂商执行"
            else:
                status = "queued"
                stage = "queued"
                status_text = "等待提交分镜任务"

            updated_at = _now()
            conn.execute(
                "UPDATE render_jobs SET status = ?, stage = ?, status_text = ?, updated_at = ? WHERE job_id = ?",
                (status, stage, status_text, updated_at, job_id),
            )
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._serialize_render_job(conn, row, include_scenes=True)

    def delete(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            payload = self._serialize_render_job(conn, row, include_scenes=True)
            conn.execute("DELETE FROM render_jobs WHERE job_id = ?", (job_id,))
            return payload

    def list_provider_configs(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM provider_configs ORDER BY sort_order ASC, provider_code ASC"
            ).fetchall()
            return [self._serialize_provider_config(row) for row in rows]

    def get_provider_config(self, provider_code: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM provider_configs WHERE provider_code = ?",
                (provider_code,),
            ).fetchone()
            if row is None:
                return None
            return self._serialize_provider_config(row)

    def upsert_provider_config(
        self,
        *,
        provider_code: str,
        display_name: str,
        enabled: bool,
        sort_order: int,
        description: str,
        provider_config_json: dict[str, Any],
        is_valid: bool,
        last_error: str | None,
    ) -> dict[str, Any]:
        now = _now()
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM provider_configs WHERE provider_code = ?", (provider_code,)).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO provider_configs (
                        provider_code, display_name, enabled, sort_order, description, config_version,
                        provider_config_json, is_valid, last_checked_at, last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        provider_code,
                        display_name,
                        1 if enabled else 0,
                        sort_order,
                        description,
                        _json_dumps(provider_config_json),
                        1 if is_valid else 0,
                        now,
                        last_error,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE provider_configs
                    SET display_name = ?, enabled = ?, sort_order = ?, description = ?, provider_config_json = ?,
                        is_valid = ?, last_checked_at = ?, last_error = ?, updated_at = ?
                    WHERE provider_code = ?
                    """,
                    (
                        display_name,
                        1 if enabled else 0,
                        sort_order,
                        description,
                        _json_dumps(provider_config_json),
                        1 if is_valid else 0,
                        now,
                        last_error,
                        now,
                        provider_code,
                    ),
                )

            row = conn.execute("SELECT * FROM provider_configs WHERE provider_code = ?", (provider_code,)).fetchone()
            return self._serialize_provider_config(row)

    def _serialize_provider_config(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "provider_code": row["provider_code"],
            "display_name": row["display_name"],
            "enabled": bool(row["enabled"]),
            "sort_order": row["sort_order"],
            "description": row["description"],
            "config_version": row["config_version"],
            "provider_config_json": _json_loads(row["provider_config_json"], {}),
            "is_valid": bool(row["is_valid"]),
            "last_checked_at": row["last_checked_at"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
