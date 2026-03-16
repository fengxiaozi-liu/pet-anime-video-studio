from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from .assets import AssetStore
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .jobs import JobStore
from .pipeline import run_job
from .schema import Storyboard

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / ".data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"

app = FastAPI(title="Pet Anime Video", version="0.1.0")

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

templates = Jinja2Templates(directory=str(ROOT / "templates"))
store = JobStore(DATA_DIR / "jobs.json")
assets = AssetStore(root_dir=UPLOAD_DIR / "assets", index_path=DATA_DIR / "assets.json")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/jobs")
def list_jobs(limit: int = 20) -> dict[str, Any]:
    return {"jobs": store.list_recent(limit=limit)}


@app.post("/api/jobs")
async def create_job(
    prompt: str = Form(""),
    storyboard_json: str | None = Form(None),
    backend: Literal["auto", "local", "cloud"] = Form("auto"),
    provider: Literal["kling", "openai", "gemini", "doubao"] = Form("kling"),
    subtitles: bool = Form(True),
    bgm_volume: float = Form(0.25),
    bgm: UploadFile | None = File(default=None),
    images: list[UploadFile] = File(default=[]),
) -> dict[str, Any]:
    if not images:
        raise HTTPException(status_code=400, detail="Please upload at least one image.")

    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for i, f in enumerate(images):
        # keep extension if present
        suffix = Path(f.filename or "image").suffix or ".png"
        out = job_dir / f"img_{i:02d}{suffix}"
        content = await f.read()
        out.write_bytes(content)
        saved_paths.append(out)

    bgm_path: Path | None = None
    if bgm is not None:
        suffix = Path(bgm.filename or "bgm").suffix or ".mp3"
        bgm_path = job_dir / f"bgm{suffix}"
        bgm_path.write_bytes(await bgm.read())

    if storyboard_json:
        try:
            sb = Storyboard.model_validate_json(storyboard_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid storyboard_json: {e}")
    else:
        # auto storyboard: split 15s across up to 3 scenes
        sb = Storyboard.autogen(prompt=prompt)

    sb = sb.with_defaults(prompt=prompt)
    # apply UI overrides
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
    )

    # fire-and-forget background work
    run_job(job_id=job_id, store=store)

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/api/assets")
def list_assets(limit: int = 50) -> dict[str, Any]:
    return {"assets": assets.list_recent(limit=limit)}


@app.post("/api/assets")
async def upload_asset(
    kind: str = Form("video"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    # kind is reserved for future expansion: video/image/audio/subtitles
    suffix = Path(file.filename or "file").suffix
    if kind == "video":
        if suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
            raise HTTPException(status_code=400, detail="unsupported video format")
    content = await file.read()
    meta = assets.add(kind=kind, filename=file.filename or "file", suffix=suffix or ".bin", bytes_data=content)
    return {"asset": meta}


@app.get("/api/assets/{asset_id}")
def download_asset(asset_id: str):
    meta = assets.get(asset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="asset not found")
    p = Path(meta["path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="asset missing")
    # Let browser download/play
    return FileResponse(path=str(p), filename=meta.get("filename") or p.name)


@app.get("/api/jobs/{job_id}/result")
def download_result(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=400, detail=f"job not done (status={job.get('status')})")

    out = Path(job["output"])
    if not out.exists():
        raise HTTPException(status_code=404, detail="result missing")

    return FileResponse(path=str(out), media_type="video/mp4", filename=f"{job_id}.mp4")
