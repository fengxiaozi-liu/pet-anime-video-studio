# Architect Review: Pet Anime Video Codebase
**Review Date**: 2026-03-21
**Project Status**: ⚠️ 3 days overdue (Target: 2026-03-17)
**Current Stage**: Functional prototype with baseline tests, lacking production security and scalability.

## 1. Executive Summary
The codebase has made significant progress in API management and test coverage (~85%). However, the current architecture is a **single-node prototype** that uses local JSON files for persistence and in-memory threading for job processing. It is highly vulnerable to data loss under load and lacks basic access control.

## 2. Critical Improvements for Professional Delivery

### Priority 1: API Security & Authentication (Security Gap)
**Current Issue**: All endpoints (`/api/jobs`, `/api/assets`) are public. Anyone with the URL can trigger expensive cloud GPU renders or delete/access private assets.
- **Files to Modify**: `backend/app/main.py`, `backend/app/config.py`
- **Implementation**:
    - Add `API_TOKEN` to `Settings` in `config.py`.
    - Implement a simple FastAPI `Security` dependency using `HTTPBearer` or `APIKeyHeader`.
    - Apply this dependency to all `/api/*` routes.
- **Why**: Prevent unauthorized API consumption and resource exhaustion.

### Priority 2: Atomic Persistence & JSON Data Safety (Scalability/Production Feature)
**Current Issue**: `JobStore` and `AssetStore` use a "read-all-modify-write-all" pattern on a single `jobs.json` file. While it uses a lock and a `.tmp` file, this will become a bottleneck as job volume grows and is prone to corruption if the process crashes during heavy I/O.
- **Files to Modify**: `backend/app/jobs.py`, `backend/app/assets.py`
- **Implementation**:
    - **Short term**: Partition JSON files by date or ID prefix (e.g., `data/jobs/2026-03.json`) to reduce write-amplification.
    - **Recommended**: Switch to **SQLite** (using `aiosqlite` or `sqlalchemy`). It is still zero-config (single file) but handles concurrent reads/writes and atomic transactions much better than raw JSON.
- **Why**: Ensure data integrity and prevent "last-write-wins" race conditions at scale.

### Priority 3: Robust Error Handling & Resource Cleanup (Missing Production Feature)
**Current Issue**: `pipeline.py` runs jobs in a `daemon=True` thread. If the server restarts, all "running" jobs stay stuck in the JSON as "running" forever. There is no cleanup for the `uploads/` directory which will fill up disk space quickly.
- **Files to Modify**: `backend/app/pipeline.py`, `backend/app/main.py`
- **Implementation**:
    - **Stale Job Recovery**: On startup (in `lifespan`), scan `JobStore` for "running" or "queued" jobs and mark them as "failed" or "interrupted".
    - **Disk Cleanup**: Implement a background task (FastAPI `RepeatTimer` or a simple cron) to delete `uploads/{job_id}` folders older than 24 hours.
- **Why**: Prevent "ghost" jobs from cluttering the UI and prevent disk-full outages.

### Priority 4: Request Validation & Rate Limiting (Security/Scalability)
**Current Issue**: The `create_job` endpoint allows uploading up to 12 images without checking file sizes. A malicious user could upload 12x100MB images to crash the server (OOM) or fill the disk.
- **Files to Modify**: `backend/app/main.py`
- **Implementation**:
    - Add a `MAX_CONTENT_LENGTH` check middleware.
    - Use `slowapi` to add rate limiting (e.g., 5 jobs per hour per IP).
    - Validate image dimensions using `Pillow` before accepting the job.
- **Why**: Protect the rendering pipeline from "Denial of Wallet" (cloud costs) and "Denial of Service" (resource exhaustion).

## 3. Implementation Roadmap
1. **Day 1 (Security)**: Implement API Token and File Size validation.
2. **Day 2 (Stability)**: Implement startup-recovery for stale jobs and disk cleanup task.
3. **Day 3 (Persistence)**: Migrate `JobStore` to SQLite to handle concurrent operations reliably.

---
**Reviewer**: Architect Agent
**Status**: Critical review submitted for implementation.