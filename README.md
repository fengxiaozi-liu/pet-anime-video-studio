# Pet Anime Video Studio (MVP)

A local-first MVP that turns **a prompt + multiple images + storyboard** into a **15s 720p MP4** via a pluggable backend.

It is engineered as a pipeline with **switchable backends**:

- **Local** backend (guaranteed): “storyboard → camera motion (Ken Burns) → crossfades → FFmpeg encode”
- **Cloud** backend (pluggable): provider adapters for **Kling/可灵**, **Gemini**, **豆包**, **OpenAI** (stubs by default)
- **Auto** backend (recommended): try cloud first, fallback to local if not configured

> Style note
>
> This project uses **descriptive style prompts** (e.g. “warm hand-drawn anime, watercolor backgrounds, cozy storybook vibe”).
>

## Features

- Upload **multiple images** (character/reference frames)
- Optional **storyboard JSON** (scenes + durations + per-scene prompts)
- Built-in **platform templates** for 抖音 / 小红书 vertical shorts
- Generates **MP4** (H.264) with crossfades and subtle motion
- Optional **BGM** + **burned-in subtitles** (SRT)
- Simple web UI + REST API

## Requirements

- Ubuntu/WSL
- Python 3.10+
- FFmpeg (`ffmpeg`)

## Quickstart

### Option A: install script (recommended)

```bash
cd pet-anime-video
./scripts/install.sh

# run
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000

# open
# http://localhost:8000
```

### Option B: manual install

```bash
cd pet-anime-video
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# ffmpeg is required for local backend
# Ubuntu/WSL: sudo apt-get update && sudo apt-get install -y ffmpeg
# macOS: brew install ffmpeg

# run
uvicorn backend.app.main:app --reload --port 8000
```

## API

### Create job

`POST /api/jobs`

Form fields:
- `prompt` (string)
- `storyboard_json` (string; optional)
- `backend` (string: `auto` | `local` | `cloud`; default `auto`)
- `provider` (string: `kling` | `gemini` | `doubao` | `openai`; default `kling`)
- `template_id` (string; optional, e.g. `douyin-15`, `xiaohongshu-35`)
- `subtitles` (bool; default `true`)
- `bgm_volume` (float; default `0.25`)
- `bgm` (file; optional)
- `images` (files; multiple)

Response: `{ "job_id": "..." }`

### Get job

`GET /api/jobs/{job_id}`

### List platform templates

`GET /api/platform-templates`

### Download result

`GET /api/jobs/{job_id}/result`

## Storyboard format

If `storyboard_json` is omitted, the server will auto-create a simple storyboard.

Example:

```json
{
  "fps": 30,
  "width": 1280,
  "height": 720,
  "duration_s": 15,
  "style": "warm hand-drawn anime, watercolor backgrounds, soft line art, cozy storybook vibe",
  "scenes": [
    {"duration_s": 5, "prompt": "A small pet hero wakes up in a sunlit room"},
    {"duration_s": 5, "prompt": "The hero walks through a quiet street with gentle wind"},
    {"duration_s": 5, "prompt": "Golden-hour ending shot, peaceful and hopeful"}
  ]
}
```

## Switching backends

- `backend=local`: runs on your machine using FFmpeg.
- `backend=cloud`: currently a stub; implement `backend/providers/cloud_provider.py`.

## Notes

- The repository does **not** ship model weights.
- This MVP is built to be easily upgraded to ComfyUI/AnimateDiff/SVD pipelines later.
