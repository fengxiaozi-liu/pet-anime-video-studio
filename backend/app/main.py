from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from .application.services import (
    CharacterImageAssistantConfigService,
    JobApplicationService,
    MaterialAssetService,
    ProviderConfigService,
    StoryAssistantConfigService,
)
from .assets import AssetStore
from .config import get_settings
from .export_package import generate_export_package
from .infrastructure.sqlite_repositories import (
    SqliteAssetRepository,
    SqliteCharacterImageAssistantConfigRepository,
    SqliteDatabase,
    SqliteProviderConfigRepository,
    SqliteRenderJobRepository,
    SqliteSceneJobRepository,
    SqliteStoryAssistantConfigRepository,
)
from .infrastructure.storage import LocalStorageService
from .pipeline import TaskWorker, run_job
from .platform_templates import get_platform_template, list_platform_templates
from .providers.cloud_dispatch import get_provider, list_registered_providers
from .schema import Storyboard
from .security import SecurityManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_BGM_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

security_manager: SecurityManager | None = None
task_worker: TaskWorker | None = None
security = HTTPBasic(auto_error=False)

settings = get_settings()
ROOT = Path(__file__).resolve().parents[2]
FRONT_ROOT = ROOT / "front"
UPLOAD_DIR = settings.UPLOAD_DIR
OUTPUT_DIR = settings.OUTPUT_DIR
DATA_DIR = settings.DATA_DIR

db = SqliteDatabase(settings.DATABASE_PATH)
scene_repo = SqliteSceneJobRepository(db)
render_repo = SqliteRenderJobRepository(db, scene_repo)
provider_repo = SqliteProviderConfigRepository(db)
story_assistant_repo = SqliteStoryAssistantConfigRepository(db)
character_image_assistant_repo = SqliteCharacterImageAssistantConfigRepository(db)
asset_repo = SqliteAssetRepository(db, settings.STORAGE_PUBLIC_BASE_URL)
storage_service = LocalStorageService(base_dir=settings.STORAGE_BASE_DIR, public_base_url=settings.STORAGE_PUBLIC_BASE_URL)
assets = AssetStore(root_dir=UPLOAD_DIR / "assets", index_path=DATA_DIR / "assets.json")


class ProviderRegistryAdapter:
    def list_registered(self) -> list[dict[str, Any]]:
        return list_registered_providers()

    def get(self, provider_code: str):
        return get_provider(provider_code)


provider_registry = ProviderRegistryAdapter()
provider_service = ProviderConfigService(provider_repo, provider_registry, settings)
story_assistant_service = StoryAssistantConfigService(story_assistant_repo, settings)
material_service = MaterialAssetService(asset_repo, storage_service)
character_image_assistant_service = CharacterImageAssistantConfigService(
    character_image_assistant_repo,
    settings,
    storage_service,
    material_service,
)
job_service = JobApplicationService(render_repo, scene_repo, provider_repo, asset_repo, settings)


class ProviderConfigUpdate(BaseModel):
    enabled: bool = False
    display_name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    provider_config_json: dict[str, Any] = {}


class ProviderValidateRequest(BaseModel):
    provider_config_json: dict[str, Any] | None = None


class StoryAssistantConfigPayload(BaseModel):
    display_name: str
    enabled: bool = False
    sort_order: int = 100
    description: str = ""
    protocol: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    system_prompt: str = ""
    temperature: float = 0.7


class StoryAssistantGenerateCharacter(BaseModel):
    name: str
    description: str = ""


class StoryAssistantGenerateRequest(BaseModel):
    assistant_code: str
    prompt: str
    aspect_ratio: str | None = None
    template_name: str | None = None
    visual_style_name: str | None = None
    visual_style_prompt: str | None = None
    characters: list[StoryAssistantGenerateCharacter] = Field(default_factory=list)


class CharacterImageAssistantConfigPayload(BaseModel):
    display_name: str
    enabled: bool = False
    sort_order: int = 100
    description: str = ""
    protocol: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    system_prompt: str = ""


class CharacterImageGenerateRequest(BaseModel):
    assistant_code: str
    character_name: str
    character_description: str = ""
    story_summary: str = ""
    story_setting: str = ""
    visual_style_name: str = ""
    visual_style_prompt: str = ""


class CharacterImageConfirmRequest(BaseModel):
    preview_image_url: str
    name: str
    description: str = ""
    prompt_fragment: str = ""
    group_name: str = "默认分组"
    sort_order: int = 100


async def verify_api_credentials(credentials: HTTPBasicCredentials | None = Depends(security)):
    if security_manager is None or not security_manager.enabled:
        return "anonymous"

    if credentials is None:
        raise HTTPException(status_code=401, detail="API credentials required", headers={"WWW-Authenticate": "Basic"})

    api_username = os.getenv("API_KEY_USERNAME", "admin")
    api_password = os.getenv("API_KEY_PASSWORD", "changeme123")
    if credentials.username != api_username or credentials.password != api_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username


async def authenticated_endpoint(user: str = Depends(verify_api_credentials)):
    if security_manager and security_manager.enabled:
        security_manager.check_rate_limit(f"auth:{user}")
    return user


def _parse_json_form(field_name: str, raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 JSON object")
    return payload


def _serialize_job(job) -> dict[str, Any]:
    return asdict(job)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global security_manager, task_worker
    logger.info("=== Starting Pet Anime Video Backend ===")
    logger.info("DEBUG: %s", settings.DEBUG)
    logger.info("DATABASE: %s", settings.DATABASE_PATH)
    logger.info("STORAGE: %s (%s)", settings.storage.provider, settings.STORAGE_BASE_DIR)

    security_enabled = os.getenv("SECURITY_ENABLED", "false").lower() == "true"
    if security_enabled:
        try:
            security_manager = SecurityManager(api_keys={}, requests_per_minute=10, requests_per_hour=100)
        except Exception as exc:
            logger.warning("Failed to initialize security: %s. Running without auth.", exc)
            security_manager = SecurityManager(api_keys={}, enabled=False)
    else:
        security_manager = SecurityManager(api_keys={}, enabled=False)

    provider_service.seed_from_config()
    story_assistant_service.seed_from_config()
    character_image_assistant_service.seed_from_config()
    configured = [item["provider_code"] for item in provider_service.list_available()]
    if configured:
        logger.info("Configured providers: %s", ", ".join(configured))
    else:
        logger.warning("No available providers configured.")
    assistants = [item["assistant_code"] for item in story_assistant_service.list_available()]
    if assistants:
        logger.info("Available story assistants: %s", ", ".join(assistants))
    else:
        logger.warning("No available story assistants configured.")
    image_assistants = [item["assistant_code"] for item in character_image_assistant_service.list_available()]
    if image_assistants:
        logger.info("Available character image assistants: %s", ", ".join(image_assistants))
    else:
        logger.warning("No available character image assistants configured.")

    task_worker = TaskWorker(
        render_repo=render_repo,
        scene_repo=scene_repo,
        app_config=settings,
        poll_interval_s=settings.worker.poll_interval_s,
        compose_enabled=settings.worker.compose_enabled,
    )
    task_worker.start()
    logger.info("=========================================")
    yield
    if task_worker is not None:
        task_worker.stop()


app = FastAPI(title="Pet Anime Video", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(FRONT_ROOT / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(settings.STORAGE_BASE_DIR)), name="media")
templates = Jinja2Templates(directory=str(FRONT_ROOT / "templates"))


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
def providers_page():
    return RedirectResponse(url="/config", status_code=307)


@app.get("/config", response_class=HTMLResponse)
def config_page(request: Request):
    return templates.TemplateResponse("providers.html", {"request": request})


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pet-anime-video"}


@app.get("/api/jobs")
def list_jobs(limit: int = 20, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"jobs": job_service.list_jobs(limit=limit)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, _user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    job = job_service.delete_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "job_id": job_id}


@app.get("/api/providers")
def list_available_providers(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"providers": provider_service.list_available()}


@app.get("/api/story-assistants")
def list_available_story_assistants(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"story_assistants": story_assistant_service.list_available()}


@app.get("/api/character-image-assistants")
def list_available_character_image_assistants(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"character_image_assistants": character_image_assistant_service.list_available()}


@app.get("/api/provider-configs")
def list_provider_configs(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"provider_configs": provider_service.list_configs_for_ui()}


@app.get("/api/story-assistant-configs")
def list_story_assistant_configs(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"story_assistant_configs": story_assistant_service.list_configs_for_ui()}


@app.get("/api/character-image-assistant-configs")
def list_character_image_assistant_configs(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"character_image_assistant_configs": character_image_assistant_service.list_configs_for_ui()}


@app.put("/api/provider-configs/{provider_code}")
def update_provider_config(
    provider_code: str,
    body: ProviderConfigUpdate,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    provider_code = provider_code.strip()
    if not provider_code:
        raise HTTPException(status_code=400, detail="provider_code is required")
    return {
        "provider_config": provider_service.update(
            provider_code,
            enabled=body.enabled,
            display_name=body.display_name,
            description=body.description,
            sort_order=body.sort_order,
            provider_config_json=body.provider_config_json,
        )
    }


@app.post("/api/provider-configs/{provider_code}/validate")
def validate_provider_config(
    provider_code: str,
    body: ProviderValidateRequest,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    current = provider_repo.get(provider_code)
    provider_config_json = body.provider_config_json if body.provider_config_json is not None else (current.provider_config_json if current else {})
    try:
        errors = provider_service.validate(provider_code, provider_config_json)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": not errors, "errors": errors}


@app.put("/api/story-assistant-configs/{assistant_code}")
def update_story_assistant_config(
    assistant_code: str,
    body: StoryAssistantConfigPayload,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    assistant_code = assistant_code.strip()
    if not assistant_code:
        raise HTTPException(status_code=400, detail="assistant_code is required")
    return {"story_assistant_config": story_assistant_service.update(assistant_code, body.model_dump())}


@app.post("/api/story-assistant-configs/{assistant_code}/validate")
def validate_story_assistant_config(
    assistant_code: str,
    body: StoryAssistantConfigPayload,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    errors = story_assistant_service.validate(body.model_dump())
    return {"ok": not errors, "errors": errors, "assistant_code": assistant_code}


@app.put("/api/character-image-assistant-configs/{assistant_code}")
def update_character_image_assistant_config(
    assistant_code: str,
    body: CharacterImageAssistantConfigPayload,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    assistant_code = assistant_code.strip()
    if not assistant_code:
        raise HTTPException(status_code=400, detail="assistant_code is required")
    return {"character_image_assistant_config": character_image_assistant_service.update(assistant_code, body.model_dump())}


@app.post("/api/character-image-assistant-configs/{assistant_code}/validate")
def validate_character_image_assistant_config(
    assistant_code: str,
    body: CharacterImageAssistantConfigPayload,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    errors = character_image_assistant_service.validate(body.model_dump())
    return {"ok": not errors, "errors": errors, "assistant_code": assistant_code}


@app.post("/api/story-assistants/generate")
def generate_story_assistant_draft(
    body: StoryAssistantGenerateRequest,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    try:
        draft = story_assistant_service.generate(
            body.assistant_code,
            prompt=prompt,
            aspect_ratio=body.aspect_ratio,
            template_name=body.template_name,
            visual_style_name=body.visual_style_name,
            visual_style_prompt=body.visual_style_prompt,
            characters=[item.model_dump() for item in body.characters],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"故事助手生成失败: {exc}") from exc
    return draft


@app.post("/api/character-image-assistants/generate")
def generate_character_image_preview(
    body: CharacterImageGenerateRequest,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    character_name = body.character_name.strip()
    if not character_name:
        raise HTTPException(status_code=400, detail="character_name is required")
    try:
        result = character_image_assistant_service.generate(
            body.assistant_code,
            character_name=character_name,
            character_description=body.character_description,
            story_summary=body.story_summary or None,
            story_setting=body.story_setting or None,
            visual_style_name=body.visual_style_name or None,
            visual_style_prompt=body.visual_style_prompt or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生图失败: {exc}") from exc
    return result


@app.post("/api/character-image-assistants/confirm")
def confirm_character_image_preview(
    body: CharacterImageConfirmRequest,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        item = character_image_assistant_service.confirm_preview(
            preview_image_url=body.preview_image_url,
            name=name,
            description=body.description,
            prompt_fragment=body.prompt_fragment,
            group_name=body.group_name,
            sort_order=body.sort_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@app.get("/api/platform-templates")
def get_platform_templates(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return {"templates": list_platform_templates()}


@app.get("/api/materials")
def get_materials(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return material_service.list_materials(enabled_only=True)


@app.get("/api/material-configs")
def get_material_configs(_user: str = Depends(authenticated_endpoint)) -> dict[str, Any]:
    return material_service.list_materials(enabled_only=False)


@app.post("/api/material-configs/{material_type}")
async def create_material_config(
    material_type: Literal["visuals", "frames", "characters", "voices", "music"],
    metadata_json: str = Form("{}"),
    file: UploadFile | None = File(default=None),
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    if file is None:
        raise HTTPException(status_code=400, detail="新增素材必须上传文件")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传的素材文件为空")
    metadata = _parse_json_form("metadata_json", metadata_json)
    try:
        item = material_service.create_asset(
            material_type,
            metadata,
            file_name=file.filename or f"{material_type}.bin",
            file_bytes=file_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@app.put("/api/material-configs/{material_type}/{item_id}")
async def update_material_config(
    material_type: Literal["visuals", "frames", "characters", "voices", "music"],
    item_id: str,
    metadata_json: str = Form("{}"),
    file: UploadFile | None = File(default=None),
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    metadata = _parse_json_form("metadata_json", metadata_json)
    file_name = None
    file_bytes = None
    if file is not None:
        file_name = file.filename or f"{material_type}.bin"
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="上传的素材文件为空")
    try:
        item = material_service.update_asset(
            material_type,
            item_id,
            metadata,
            file_name=file_name,
            file_bytes=file_bytes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="material not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@app.delete("/api/material-configs/{material_type}/{item_id}")
def delete_material_config(
    material_type: Literal["visuals", "frames", "characters", "voices", "music"],
    item_id: str,
    _user: str = Depends(authenticated_endpoint),
) -> dict[str, Any]:
    item = material_service.delete_asset(material_type, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="material not found")
    return {"ok": True, "item": item}


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
    opening_frame: UploadFile | None = File(default=None),
    ending_frame: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    if not (0.0 <= bgm_volume <= 2.0):
        raise HTTPException(status_code=400, detail="bgm_volume must be between 0.0 and 2.0.")

    template = get_platform_template(template_id)
    if template_id and template is None:
        raise HTTPException(status_code=400, detail=f"Unknown template_id: {template_id}")

    if storyboard_json:
        try:
            sb = Storyboard.model_validate_json(storyboard_json)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid storyboard_json: {exc}") from exc
    else:
        default_duration = float(template.get("duration_s", 15.0)) if template else 15.0
        sb = Storyboard.autogen(prompt=prompt, duration_s=default_duration)

    sb = sb.apply_template(template).with_defaults(prompt=prompt)
    sb = sb.model_copy(update={"subtitles": subtitles, "bgm_volume": bgm_volume})
    if not sb.aspect_ratio:
        raise HTTPException(status_code=400, detail="storyboard_json 缺少 aspect_ratio。")

    bgm_path: str | None = None
    if bgm is not None:
        suffix = (Path(bgm.filename or "bgm").suffix or ".mp3").lower()
        if suffix not in ALLOWED_BGM_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported BGM format: {suffix}")
        bgm_bytes = await bgm.read()
        if not bgm_bytes:
            raise HTTPException(status_code=400, detail="Uploaded BGM file is empty.")
        stored = storage_service.save_bytes(filename=bgm.filename or f"bgm{suffix}", data=bgm_bytes, category="job-bgm")
        bgm_path = str(settings.STORAGE_BASE_DIR / stored.path)

    if opening_frame is not None:
        opening_bytes = await opening_frame.read()
        if not opening_bytes:
            raise HTTPException(status_code=400, detail="Uploaded opening_frame file is empty.")
        stored = storage_service.save_bytes(
            filename=opening_frame.filename or "opening-frame.png",
            data=opening_bytes,
            category="job-frames",
        )
        sb = sb.model_copy(update={"opening_frame_url": stored.public_url})

    if ending_frame is not None:
        ending_bytes = await ending_frame.read()
        if not ending_bytes:
            raise HTTPException(status_code=400, detail="Uploaded ending_frame file is empty.")
        stored = storage_service.save_bytes(
            filename=ending_frame.filename or "ending-frame.png",
            data=ending_bytes,
            category="job-frames",
        )
        sb = sb.model_copy(update={"ending_frame_url": stored.public_url})

    try:
        job_id = job_service.create_job(
            prompt=prompt,
            provider=provider,
            backend=backend,
            storyboard=sb.model_dump(),
            template_id=sb.template_id,
            bgm_path=bgm_path,
            output_path=str(OUTPUT_DIR / f"{os.urandom(8).hex()}.mp4"),
            images=[],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_job(job_id=job_id, render_repo=render_repo)
    return {"job_id": job_id}


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
    job = render_repo.refresh_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.status})")
    out = Path(job.final_video_url or job.output_path)
    if not out.exists():
        raise HTTPException(status_code=404, detail="result missing")
    return FileResponse(path=str(out), media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/api/jobs/{job_id}/export/package")
def export_package(job_id: str, _user: str = Depends(authenticated_endpoint)):
    job = render_repo.refresh_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.status})")

    zip_path = generate_export_package(job_id, render_repo, OUTPUT_DIR / "exports")
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=500, detail="failed to generate export package")

    return FileResponse(path=str(zip_path), media_type="application/zip", filename=f"PetClip_{job_id[:8]}_export.zip")


@app.get("/api/jobs/{job_id}/export/cover")
def export_cover(job_id: str, _user: str = Depends(authenticated_endpoint)):
    job = render_repo.refresh_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.status})")

    video_path = Path(job.final_video_url or job.output_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="video missing")

    template = get_platform_template(job.template_id)
    cover_w = (template or {}).get("cover_width", 1080)
    cover_h = (template or {}).get("cover_height", 1920)

    cover_path = video_path.with_suffix(".cover.png")
    if not cover_path.exists():
        from .export_package import _extract_cover  # noqa: PLC0415

        extracted = _extract_cover(video_path, cover_w, cover_h)
        if not extracted:
            raise HTTPException(status_code=500, detail="failed to extract cover frame")
        cover_path = extracted

    return FileResponse(path=str(cover_path), media_type="image/png", filename=f"{job_id}_cover.png")
