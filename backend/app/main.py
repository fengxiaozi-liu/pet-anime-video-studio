from __future__ import annotations

import logging
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .assets import AssetStore
from .config import get_settings
from .export_package import generate_export_package
from .jobs import JobStore
from .pipeline import TaskWorker, run_job
from .platform_templates import get_platform_template, list_platform_templates
from .providers.cloud_dispatch import _PROVIDERS, get_provider, list_registered_providers
from .schema import Storyboard
from .security import SecurityManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_BGM_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

# Global security manager instance
security_manager: SecurityManager | None = None
task_worker: TaskWorker | None = None
security = HTTPBasic(auto_error=False)

async def verify_api_credentials(credentials: HTTPBasicCredentials | None = Depends(security)):
    """Verify HTTP Basic Auth credentials."""
    if security_manager is None or not security_manager.enabled:
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="API credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Validate credentials against configured values
    api_username = os.getenv("API_KEY_USERNAME", "admin")
    api_password = os.getenv("API_KEY_PASSWORD", "changeme123")
    
    if credentials.username != api_username or credentials.password != api_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return credentials.username


async def authenticated_endpoint(user: str = Depends(verify_api_credentials)):
    """Dependency for authenticated endpoints with rate limiting."""
    if security_manager and security_manager.enabled:
        user_id = f"auth:{user}"
        security_manager.check_rate_limit(user_id)
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Log provider configuration status and initialize security
    global security_manager, task_worker
    settings = get_settings()
    logger.info("=== Starting Pet Anime Video Backend ===")
    logger.info(f"DEBUG: {settings.DEBUG}")
    logger.info(f"UPLOAD_DIR: {settings.UPLOAD_DIR}")
    logger.info(f"OUTPUT_DIR: {settings.OUTPUT_DIR}")

    # Initialize security manager
    security_enabled = os.getenv("SECURITY_ENABLED", "false").lower() == "true"
    if security_enabled:
        try:
            security_manager = SecurityManager(
                api_keys={},
                requests_per_minute=10,
                requests_per_hour=100,
            )
            logger.info("Security manager initialized with rate limiting (10 req/min, 100 req/hour)")
        except Exception as e:
            logger.warning(f"Failed to initialize security: {e}. Running without auth.")
            security_manager = SecurityManager(api_keys={}, enabled=False)
    else:
        security_manager = SecurityManager(api_keys={}, enabled=False)
        logger.info("Security disabled (SECURITY_ENABLED=false, default for local development)")

    for item in list_registered_providers():
        provider = get_provider(item["provider_code"])
        config = {
            "app_key": settings.JIMENG_APP_KEY or "",
            "app_secret": settings.JIMENG_APP_SECRET or "",
            "req_key": settings.JIMENG_REQ_KEY,
            "base_url": "https://visual.volcengineapi.com",
            "mock_mode": False,
        }
        ok, error = provider.healthcheck(config)
        store.seed_provider_config(
            provider_code=item["provider_code"],
            display_name=item["display_name"],
            description=item["description"],
            sort_order=item["sort_order"],
            provider_config_json=config,
            enabled=ok,
            is_valid=ok,
            last_error=error,
        )

    configured_providers = [
        item["provider_code"] for item in store.list_provider_configs() if item["enabled"] and item["is_valid"]
    ]
    if configured_providers:
        logger.info("Configured Providers: %s", ", ".join(configured_providers))
    else:
        logger.warning("No configured providers available. Use /providers to configure Provider credentials.")

    task_worker = TaskWorker(store=store, upload_dir=UPLOAD_DIR)
    task_worker.start()
    logger.info("=========================================")
    yield
    if task_worker is not None:
        task_worker.stop()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / ".data"
settings = get_settings()
UPLOAD_DIR = settings.UPLOAD_DIR
OUTPUT_DIR = settings.OUTPUT_DIR

app = FastAPI(title="Pet Anime Video", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

templates = Jinja2Templates(directory=str(ROOT / "templates"))
store = JobStore(settings.DATABASE_PATH)
assets = AssetStore(root_dir=UPLOAD_DIR / "assets", index_path=DATA_DIR / "assets.json")


class ProviderConfigUpdate(BaseModel):
    enabled: bool = False
    provider_config_json: dict[str, Any] = {}


class ProviderValidateRequest(BaseModel):
    provider_config_json: dict[str, Any] | None = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/studio", response_class=HTMLResponse)
def studio(request: Request):
    return templates.TemplateResponse("studio.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
def tasks(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})


@app.get("/tasks/{job_id}", response_class=HTMLResponse)
def task_detail(request: Request, job_id: str):
    return templates.TemplateResponse("task_detail.html", {"request": request, "job_id": job_id})


@app.get("/providers", response_class=HTMLResponse)
def providers_page(request: Request):
    return templates.TemplateResponse("providers.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "pet-anime-video"}


@app.get("/api/jobs")
def list_jobs(limit: int = 20, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"jobs": store.list_recent(limit=limit)}


@app.get("/api/providers")
def list_available_providers(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    configs = {item["provider_code"]: item for item in store.list_provider_configs()}
    items: list[dict[str, Any]] = []
    for provider in list_registered_providers():
        config = configs.get(provider["provider_code"])
        if config and config["enabled"] and config["is_valid"]:
            items.append(
                {
                    "provider_code": provider["provider_code"],
                    "display_name": provider["display_name"],
                    "description": provider["description"],
                    "capabilities": provider["capabilities"],
                }
            )
    return {"providers": items}


@app.get("/api/provider-configs")
def list_provider_configs(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    configs = {item["provider_code"]: item for item in store.list_provider_configs()}
    payload: list[dict[str, Any]] = []
    for provider in list_registered_providers():
        config = configs.get(provider["provider_code"]) or {
            "provider_code": provider["provider_code"],
            "display_name": provider["display_name"],
            "enabled": False,
            "sort_order": provider["sort_order"],
            "description": provider["description"],
            "provider_config_json": {},
            "is_valid": False,
            "last_checked_at": None,
            "last_error": "尚未配置",
        }
        payload.append(
            {
                **config,
                "display_name": provider["display_name"],
                "description": provider["description"],
                "capabilities": provider["capabilities"],
                "config_fields": provider["config_fields"],
            }
        )
    return {"provider_configs": payload}


@app.put("/api/provider-configs/{provider_code}")
def update_provider_config(
    provider_code: str,
    body: ProviderConfigUpdate,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    provider = get_provider(provider_code)
    errors = provider.validate_config(body.provider_config_json)
    item = next((p for p in list_registered_providers() if p["provider_code"] == provider_code), None)
    if item is None:
        raise HTTPException(status_code=404, detail="provider not found")
    config = store.upsert_provider_config(
        provider_code=provider_code,
        display_name=item["display_name"],
        description=item["description"],
        sort_order=item["sort_order"],
        provider_config_json=body.provider_config_json,
        enabled=body.enabled,
        is_valid=not errors,
        last_error=None if not errors else "；".join(errors),
    )
    return {"provider_config": config}


@app.post("/api/provider-configs/{provider_code}/validate")
def validate_provider_config(
    provider_code: str,
    body: ProviderValidateRequest,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    provider = get_provider(provider_code)
    current = store.get_provider_config(provider_code) or {}
    provider_config_json = body.provider_config_json if body.provider_config_json is not None else current.get("provider_config_json", {})
    errors = provider.validate_config(provider_config_json)
    return {"ok": not errors, "errors": errors}


@app.get("/api/platform-templates")
def get_platform_templates(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    templates = list_platform_templates()
    return {"templates": templates}


@app.post("/api/jobs")
async def create_job(
    _user: str = Depends(authenticated_endpoint),
    prompt: str = Form(""),
    storyboard_json: str | None = Form(None),
    backend: Literal["cloud"] = Form("cloud"),
    provider: str = Form("jimeng"),
    template_id: str | None = Form(None),
    subtitles: bool = Form(True),
    bgm_volume: float = Form(0.25),
    bgm: UploadFile | None = File(default=None),
    images: list[UploadFile] = File(default=[]),
) -> dict[str, Any]:
    if len(images) > 12:
        raise HTTPException(status_code=400, detail="Please upload at most 12 images per job.")
    if not (0.0 <= bgm_volume <= 2.0):
        raise HTTPException(status_code=400, detail="bgm_volume must be between 0.0 and 2.0.")
    provider_meta = store.get_provider_config(provider)
    if provider_meta is None or not provider_meta.get("enabled") or not provider_meta.get("is_valid"):
        raise HTTPException(status_code=400, detail=f"Provider {provider} 未配置或未启用。")

    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for i, f in enumerate(images):
        suffix = (Path(f.filename or "image").suffix or ".png").lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported image format: {suffix}")
        out = job_dir / f"img_{i:02d}{suffix}"
        content = await f.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"Image {f.filename or i} is empty.")
        out.write_bytes(content)
        saved_paths.append(out)

    bgm_path: Path | None = None
    if bgm is not None:
        suffix = (Path(bgm.filename or "bgm").suffix or ".mp3").lower()
        if suffix not in ALLOWED_BGM_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported BGM format: {suffix}")
        bgm_bytes = await bgm.read()
        if not bgm_bytes:
            raise HTTPException(status_code=400, detail="Uploaded BGM file is empty.")
        bgm_path = job_dir / f"bgm{suffix}"
        bgm_path.write_bytes(bgm_bytes)

    template = get_platform_template(template_id)
    if template_id and template is None:
        raise HTTPException(status_code=400, detail=f"Unknown template_id: {template_id}")

    if storyboard_json:
        try:
            sb = Storyboard.model_validate_json(storyboard_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid storyboard_json: {e}")
    else:
        default_duration = float(template.get("duration_s", 15.0)) if template else 15.0
        sb = Storyboard.autogen(prompt=prompt, duration_s=default_duration)

    sb = sb.apply_template(template).with_defaults(prompt=prompt)
    sb.subtitles = subtitles
    sb.bgm_volume = bgm_volume

    store.create(
        job_id=job_id,
        backend=backend,
        provider=provider,
        prompt=prompt,
        storyboard=sb.model_dump(),
        images=[str(p) for p in saved_paths],
        bgm=str(bgm_path) if bgm_path else None,
        output=str((OUTPUT_DIR / f"{job_id}.mp4")),
        image_count=len(saved_paths),
        requested_backend=backend,
        requested_provider=provider,
        template_id=sb.template_id,
        template_name=sb.template_name,
        platform=sb.platform,
    )

    run_job(job_id=job_id, store=store)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    store.refresh_render_job_status(job_id)
    job = store.get(job_id) or job
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    job = store.delete(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    upload_dir = UPLOAD_DIR / job_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    output_path = Path(job.get("final_video_url") or job.get("output", ""))
    if output_path.exists():
        output_path.unlink(missing_ok=True)

    cover_path = Path(job.get("final_cover_url") or output_path.with_suffix(".cover.png"))
    if cover_path.exists():
        cover_path.unlink(missing_ok=True)

    export_zip = OUTPUT_DIR / "exports" / f"PetClip_{job_id[:8]}_export.zip"
    if export_zip.exists():
        export_zip.unlink(missing_ok=True)

    return {"ok": True, "job_id": job_id}


@app.get("/api/assets")
def list_assets(limit: int = 50, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"assets": assets.list_recent(limit=limit)}


@app.post("/api/assets")
async def upload_asset(
    _user: str = Depends(authenticated_endpoint),
    kind: str = Form("video"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    suffix = Path(file.filename or "file").suffix
    if kind == "video" and suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="unsupported video format")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="uploaded asset is empty")
    meta = assets.add(kind=kind, filename=file.filename or "file", suffix=suffix or ".bin", bytes_data=content)
    return {"asset": meta}


@app.get("/api/assets/{asset_id}")
def download_asset(asset_id: str, _user: str = Depends(authenticated_endpoint)):
    meta = assets.get(asset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="asset not found")
    p = Path(meta["path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="asset missing")
    return FileResponse(path=str(p), filename=meta.get("filename") or p.name)


@app.get("/api/jobs/{job_id}/result")
def download_result(job_id: str, _user: str = Depends(authenticated_endpoint)):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.get('status')})")

    out = Path(job.get("final_video_url") or job["output"])
    if not out.exists():
        raise HTTPException(status_code=404, detail="result missing")

    return FileResponse(path=str(out), media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/api/jobs/{job_id}/export/package")
def export_package(job_id: str, _user: str = Depends(authenticated_endpoint)):
    """Generate and download the complete export ZIP (video + cover + caption + hashtags + project.json)."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.get('status')})")

    zip_path = generate_export_package(job_id, store, OUTPUT_DIR / "exports")
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=500, detail="failed to generate export package")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"PetClip_{job_id[:8]}_export.zip",
    )


@app.get("/api/jobs/{job_id}/export/cover")
def export_cover(job_id: str, _user: str = Depends(authenticated_endpoint)):
    """Extract and download the cover PNG for a finished job."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.get('status')})")

    video_path = Path(job.get("output", ""))
    if job.get("final_video_url"):
        video_path = Path(job["final_video_url"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="video missing")

    template = get_platform_template(job.get("template_id"))
    cover_w = (template or {}).get("cover_width", 1080)
    cover_h = (template or {}).get("cover_height", 1920)

    cover_path = video_path.with_suffix(".cover.png")
    # Re-generate if missing (lazy generation on first request)
    if not cover_path.exists():
        from .export_package import _extract_cover  # noqa: PLC0415
        extracted = _extract_cover(video_path, cover_w, cover_h)
        if not extracted:
            raise HTTPException(status_code=500, detail="failed to extract cover frame")
        cover_path = extracted

    return FileResponse(path=str(cover_path), media_type="image/png", filename=f"{job_id}_cover.png")
