# API Reference - Pet Anime Video

> **Base URL**: `http://localhost:8000` (local)  
> **Authentication**: HTTP Basic Auth (configurable)

All endpoints except `/` and `/health` require authentication by default.  
Set `SECURITY_ENABLED=false` in your environment to disable authentication for development.

---

## Table of Contents

- [Health](#health-check)
- [Jobs](#jobs)
- [Assets](#assets)
- [Platform Templates](#platform-templates)

---

## Health Check

### `GET /health`

Health check endpoint for container orchestration and load balancers.

**Authentication**: None required.

**Response** `200 OK`:
```json
{
  "status": "healthy",
  "service": "pet-anime-video"
}
```

---

## Jobs

### `GET /api/jobs`

List recent jobs.

**Authentication**: Required (HTTP Basic)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `20` | Max number of jobs to return (1-100) |

**Response** `200 OK`:
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "done",
      "stage": "complete",
      "backend": "local",
      "provider": "kling",
      "prompt": "A cat exploring a magical forest",
      "created_at": "2026-03-21T09:00:00Z",
      "completed_at": "2026-03-21T09:02:30Z",
      "output": "/app/outputs/550e8400...mp4",
      "image_count": 4,
      "error": null
    }
  ]
}
```

**Job Status Values**:

| Status | Description |
|--------|-------------|
| `pending` | Job created, not yet started |
| `running` | Currently processing |
| `done` | Successfully completed |
| `error` | Failed with an error |

---

### `POST /api/jobs`

Create a new video generation job.

**Authentication**: Required (HTTP Basic)

**Content-Type**: `multipart/form-data`

**Form Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `images` | list[UploadFile] | ✅ Yes | - | 1-12 images (PNG, JPG, JPEG, WebP, GIF) |
| `prompt` | string | No | `""` | Scene narration / story prompt |
| `backend` | string | No | `"auto"` | `auto`, `local`, or `cloud` |
| `provider` | string | No | `"kling"` | AI provider: `kling`, `openai`, `gemini`, `doubao` |
| `template_id` | string | No | `null` | Platform template ID (see `/api/platform-templates`) |
| `storyboard_json` | string | No | `null` | Full storyboard as JSON string |
| `subtitles` | boolean | No | `true` | Burn subtitles into video |
| `bgm_volume` | float | No | `0.25` | BGM volume (0.0 - 2.0) |
| `bgm` | UploadFile | No | `null` | Background music file (MP3, WAV, M4A, AAC, OGG) |

**Example** (curl):

```bash
curl -X POST http://localhost:8000/api/jobs \
  -u admin:changeme123 \
  -F "images=@/path/to/cat.jpg" \
  -F "prompt=A fluffy cat wandering through a dreamy anime landscape" \
  -F "backend=auto" \
  -F "provider=kling" \
  -F "subtitles=true" \
  -F "bgm_volume=0.3"
```

**Example** (Python):

```python
import requests

url = "http://localhost:8000/api/jobs"
auth = ("admin", "changeme123")

with open("cat.jpg", "rb") as f:
    files = {"images": f}
    data = {
        "prompt": "A fluffy cat in a magical anime world",
        "backend": "auto",
        "provider": "kling",
        "subtitles": True,
        "bgm_volume": 0.3,
    }
    resp = requests.post(url, auth=auth, data=data, files=files)
    print(resp.json())  # {"job_id": "..."}
```

**Response** `200 OK`:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses**:

| Status | Detail |
|--------|--------|
| `400` | `"Please upload at least one image."` |
| `400` | `"Please upload at most 12 images per job."` |
| `400` | `"bgm_volume must be between 0.0 and 2.0."` |
| `400` | `"Unsupported image format: .bmp"` |
| `401` | `"Invalid credentials"` |
| `429` | `"Rate limit exceeded. Try again later."` |

---

### `GET /api/jobs/{job_id}`

Get details for a specific job.

**Authentication**: Required (HTTP Basic)

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string (UUID) | The job ID returned from `POST /api/jobs` |

**Response** `200 OK`:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "stage": "complete",
  "backend": "local",
  "provider": "kling",
  "prompt": "A cat exploring a magical forest",
  "created_at": "2026-03-21T09:00:00Z",
  "started_at": "2026-03-21T09:00:01Z",
  "completed_at": "2026-03-21T09:02:30Z",
  "images": ["/app/uploads/550e.../img_00.png"],
  "bgm": "/app/uploads/550e.../bgm.mp3",
  "output": "/app/outputs/550e8400...mp4",
  "image_count": 4,
  "error": null,
  "storyboard": {
    "fps": 30,
    "width": 1280,
    "height": 720,
    "duration_s": 15.0,
    "subtitles": true,
    "bgm_volume": 0.25,
    "scenes": [...]
  }
}
```

**Error Responses**:

| Status | Detail |
|--------|--------|
| `404` | `"job not found"` |

---

### `GET /api/jobs/{job_id}/result`

Download the generated video file.

**Authentication**: Required (HTTP Basic)

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string (UUID) | The job ID |

**Response** `200 OK`:  
`Content-Type: video/mp4`  
`Content-Disposition: attachment; filename="{job_id}.mp4"`

**Error Responses**:

| Status | Detail |
|--------|--------|
| `400` | `"job not done (status=pending)"` |
| `404` | `"job not found"` |
| `404` | `"result missing"` |

---

## Assets

### `GET /api/assets`

List recent uploaded assets.

**Authentication**: Required (HTTP Basic)

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `50` | Max number of assets to return |

**Response** `200 OK`:
```json
{
  "assets": [
    {
      "asset_id": "ast_abc123",
      "kind": "video",
      "filename": "sample.mp4",
      "path": "/app/uploads/assets/ast_abc123.mp4",
      "size": 1048576,
      "uploaded_at": "2026-03-21T09:00:00Z"
    }
  ]
}
```

---

### `POST /api/assets`

Upload a reusable asset (video or other media).

**Authentication**: Required (HTTP Basic)

**Form Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | UploadFile | ✅ Yes | The file to upload |
| `kind` | string | No (`"video"`) | Asset kind: `"video"` |

**Supported formats**: `.mp4`, `.mov`, `.mkv`, `.webm`

**Example**:

```bash
curl -X POST http://localhost:8000/api/assets \
  -u admin:changeme123 \
  -F "file=@/path/to/bgm.mp3" \
  -F "kind=video"
```

**Response** `200 OK`:
```json
{
  "asset": {
    "asset_id": "ast_abc123",
    "kind": "video",
    "filename": "bgm.mp3",
    "path": "/app/uploads/assets/ast_abc123.mp3",
    "size": 3145728,
    "uploaded_at": "2026-03-21T09:00:00Z"
  }
}
```

---

### `GET /api/assets/{asset_id}`

Download a previously uploaded asset.

**Authentication**: Required (HTTP Basic)

**Response** `200 OK`:  
`Content-Type: application/octet-stream`  
`Content-Disposition: attachment; filename="{filename}"`

---

## Platform Templates

### `GET /api/platform-templates`

List available platform-specific video templates.

**Authentication**: Required (HTTP Basic)

**Response** `200 OK`:
```json
{
  "templates": [
    {
      "id": "tiktok_9_16",
      "name": "TikTok 9:16",
      "platform": "tiktok",
      "width": 1080,
      "height": 1920,
      "duration_s": 15.0,
      "cover_width": 1080,
      "cover_height": 1920,
      "subtitle_safe_margin": 180
    },
    {
      "id": "youtube_short",
      "name": "YouTube Shorts 9:16",
      "platform": "youtube",
      "width": 1080,
      "height": 1920,
      "duration_s": 15.0,
      "cover_width": 1080,
      "cover_height": 1920,
      "subtitle_safe_margin": 180
    },
    {
      "id": "instagram_reels",
      "name": "Instagram Reels 9:16",
      "platform": "instagram",
      "width": 1080,
      "height": 1920,
      "duration_s": 15.0,
      "cover_width": 1080,
      "cover_height": 1920,
      "subtitle_safe_margin": 180
    },
    {
      "id": "wechat_short",
      "name": "WeChat Short Video 9:16",
      "platform": "wechat",
      "width": 1080,
      "height": 1920,
      "duration_s": 15.0,
      "cover_width": 1080,
      "cover_height": 1920,
      "subtitle_safe_margin": 180
    },
    {
      "id": "twitter_video",
      "name": "Twitter/X Video 16:9",
      "platform": "twitter",
      "width": 1280,
      "height": 720,
      "duration_s": 15.0,
      "cover_width": 1280,
      "cover_height": 720,
      "subtitle_safe_margin": 180
    },
    {
      "id": "youtube_16_9",
      "name": "YouTube 16:9",
      "platform": "youtube",
      "width": 1920,
      "height": 1080,
      "duration_s": 15.0,
      "cover_width": 1920,
      "cover_height": 1080,
      "subtitle_safe_margin": 180
    }
  ]
}
```

---

## Storyboard Schema

When passing a custom `storyboard_json` to `POST /api/jobs`, use this structure:

```json
{
  "template_id": "youtube_16_9",
  "template_name": "YouTube 16:9",
  "platform": "youtube",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "duration_s": 15.0,
  "style": "warm hand-drawn anime, watercolor backgrounds, soft line art, cozy storybook vibe, gentle lighting",
  "subtitles": true,
  "bgm_volume": 0.25,
  "x264_preset": "veryfast",
  "x264_crf": 26,
  "x264_tune": "stillimage",
  "keep_tmp": false,
  "scenes": [
    {
      "duration_s": 5.0,
      "prompt": "A fluffy orange cat sitting on a windowsill",
      "subtitle": "Whiskers dreams of adventures..."
    },
    {
      "duration_s": 5.0,
      "prompt": "The cat leaps into a magical forest",
      "subtitle": "But today, anything is possible!"
    },
    {
      "duration_s": 5.0,
      "prompt": "The cat returns home happy",
      "subtitle": "Home sweet home."
    }
  ]
}
```

**Storyboard Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `template_id` | string | null | Platform template ID |
| `fps` | integer | `30` | Frames per second (12-60) |
| `width` | integer | `1280` | Video width in pixels (320-3840) |
| `height` | integer | `720` | Video height in pixels (240-2160) |
| `duration_s` | float | `15.0` | Total video duration in seconds (1-120) |
| `style` | string | (anime style) | Visual style description |
| `subtitles` | boolean | `true` | Burn subtitles into video |
| `bgm_volume` | float | `0.25` | BGM volume (0.0-2.0) |
| `x264_preset` | string | `"veryfast"` | FFmpeg encoding speed preset |
| `x264_crf` | integer | `26` | FFmpeg CRF quality (16=best, 34=worst) |
| `x264_tune` | string | `"stillimage"` | FFmpeg x264 tune parameter |
| `keep_tmp` | boolean | `false` | Keep temporary files after rendering |
| `scenes` | list[Scene] | auto-generated | Scene definitions |

**Scene Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `duration_s` | float | ✅ Yes | Scene duration in seconds (0.5-60) |
| `prompt` | string | No | Scene description / narration |
| `subtitle` | string | No | Subtitle text to display for this scene |

---

## Authentication

### HTTP Basic Auth

All authenticated endpoints use HTTP Basic Auth.

**Default credentials** (change in production!):

| Field | Default Value |
|-------|--------------|
| Username | `admin` |
| Password | `changeme123` |

**Disable authentication** for development:

```env
SECURITY_ENABLED=false
```

**Change credentials**:

```env
API_KEY_USERNAME=myuser
API_KEY_PASSWORD=mystrongpassword
```

### Rate Limiting

When `SECURITY_ENABLED=true`:
- **10 requests/minute** per user
- **100 requests/hour** per user

---

## Error Format

All errors follow this structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```
