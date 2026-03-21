from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

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
from .pipeline import run_job
from .platform_templates import get_platform_template, list_platform_templates
from .providers.cloud_dispatch import _PROVIDERS
from .schema import Storyboard
from .security import SecurityManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_BGM_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

# Global security manager instance
security_manager: SecurityManager | None = None
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
        if not await security_manager.check_rate_limit(user_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Log provider configuration status and initialize security
    global security_manager
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

    configured_providers = []
    for name, provider in _PROVIDERS.items():
        if provider.is_configured():
            configured_providers.append(name)

    if configured_providers:
        logger.info(f"Configured Cloud Providers: {', '.join(configured_providers)}")
    else:
        logger.warning("No cloud providers are configured (API keys missing). Use backend=local/auto.")
    logger.info("=========================================")
    yield
    # Shutdown logic if needed

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / ".data"
settings = get_settings()
UPLOAD_DIR = settings.UPLOAD_DIR
OUTPUT_DIR = settings.OUTPUT_DIR

app = FastAPI(title="Pet Anime Video", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

templates = Jinja2Templates(directory=str(ROOT / "templates"))
store = JobStore(DATA_DIR / "jobs.json")
assets = AssetStore(root_dir=UPLOAD_DIR / "assets", index_path=DATA_DIR / "assets.json")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "pet-anime-video"}


@app.get("/api/jobs")
def list_jobs(limit: int = 20, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"jobs": store.list_recent(limit=limit)}


@app.get("/api/platform-templates")
def get_platform_templates(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    templates = list_platform_templates()
    return {"templates": templates}


@app.post("/api/jobs")
async def create_job(
    _user: str = Depends(authenticated_endpoint),
    prompt: str = Form(""),
    storyboard_json: str | None = Form(None),
    backend: Literal["auto", "local", "cloud"] = Form("auto"),
    provider: Literal["kling", "openai", "gemini", "doubao"] = Form("kling"),
    template_id: str | None = Form(None),
    subtitles: bool = Form(True),
    bgm_volume: float = Form(0.25),
    bgm: UploadFile | None = File(default=None),
    images: list[UploadFile] = File(default=[]),
) -> dict[str, Any]:
    if not images:
        raise HTTPException(status_code=400, detail="Please upload at least one image.")
    if len(images) > 12:
        raise HTTPException(status_code=400, detail="Please upload at most 12 images per job.")
    if not (0.0 <= bgm_volume <= 2.0):
        raise HTTPException(status_code=400, detail="bgm_volume must be between 0.0 and 2.0.")

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
    return job


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

    out = Path(job["output"])
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
