# DEVM4_AUDIT.md — Backend Developer Assessment

**Project:** pet-anime-video backend
**Date:** 2026-03-21
**Auditor:** Developer sub-agent

---

## 1. Non-Pure-Python Dependencies

| Package | Version | Native? | Risk |
|---|---|---|---|
| `pillow` | 10.4.0 | ⚠️ YES — requires libjpeg, zlib, libpng libs at build time | Build stage installs `gcc` + `libpq-dev` but is **missing Pillow-specific dev libs** (`libjpeg-dev zlib1g-dev libpng-dev`). Pillow wheels ship pre-built binaries for common platforms, so `pip install --no-cache-dir --user` in the builder stage will grab a wheel and skip compilation — **this works but is fragile**. If the platform has no matching wheel, the install silently fails or produces a broken Pillow. |
| All others (`fastapi`, `uvicorn`, `pydantic`, `httpx`, `jinja2`, `pytest`, etc.) | — | Pure Python wheels | Low risk. |

**Action required:** Add `libjpeg-dev zlib1g-dev libtiff5-dev libpng-dev` to the builder `apt-get install` line to guarantee Pillow can compile from source if no wheel matches.

---

## 2. System-Level Requirements

- **FFmpeg** — installed in runtime stage via `apt-get install ffmpeg`. No version pinned. Debian 12 (bookworm) ships FFmpeg 4.4.1; this is generally sufficient for the `moviepy`/`ffmpeg-python`/`cv2` video pipeline, but version mismatches with specific codecs (e.g. `h264_qsv`, `hevc_nvenc`) can cause silent failures. Pin a minimum: `ffmpeg >= 4.4` or use `ffmpeg-static` if deterministic builds matter.
- **Python 3.10** — used in both builder and runtime stages. Consistent. No `python3.10` version pin beyond the base image tag.
- **No `__main__.py`** exists — the backend is NOT directly runnable via `python -m app`. Entry is entirely via `uvicorn app.main:app` (Dockerfile `CMD` and local dev).

---

## 3. Import-Time Issues

**Eager top-level imports** in `app/main.py`:
```python
from .assets import AssetStore       # runs on import
from .jobs import JobStore           # runs on import
from .pipeline import run_job        # runs on import
from .export_package import generate_export_package  # runs on import
from .providers.cloud_dispatch import _PROVIDERS    # runs on import
from .security import SecurityManager
```

All of these fire immediately when `main.py` is imported (by uvicorn on startup). If any of these submodules have **heavy import-time side effects** (e.g., `local_provider.py` importing `cv2` or `torch`, `pipeline.py` importing heavy ML libs), startup will be slow and memory footprint high even if those features are never used. The `local_provider` is imported eagerly at module scope — worth auditing.

**`__file__` usage** — `ROOT = Path(__file__).resolve().parents[2]` in `main.py` is safe; uvicorn resolves `__file__` correctly. For PyInstaller-style packagers it also works because `__file__` still points inside the extracted bundle.

**Late local import** inside `export_cover()`:
```python
from .export_package import _extract_cover  # noqa: PLC0415
```
This is inside the endpoint function — fine for lazy loading, no issue.

---

## 4. Startup Entry Point

- **Dockerfile `CMD`:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **No `__main__.py`**, no `python -m app` entry. The app is exclusively `uvicorn`-hosted.
- `app/main.py` creates the `FastAPI` app instance at module scope (`app = FastAPI(...)`) — uvicorn imports `app.main:app` and the lifespan context manager fires on startup.

---

## Summary of Issues

| # | Severity | Issue |
|---|---|---|
| 1 | **Medium** | Builder stage missing Pillow build deps — wheel-only fallback is fragile |
| 2 | **Low** | FFmpeg not version-pinned in runtime stage |
| 3 | **Low** | No `__main__.py` — not directly runnable via `python -m app` |
| 4 | **Info** | Eager imports of providers/pipeline/assets on every startup; heavy ML libs in `local_provider` could slow boot |
