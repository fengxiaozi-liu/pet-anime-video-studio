# Configuration Reference - Pet Anime Video

All configuration is done via environment variables. Create a `.env` file in the project root (or `backend/` directory when running outside Docker).

---

## Getting Started

1. Copy the example environment file:
   ```bash
   cp .env.example backend/.env
   ```

2. Edit `backend/.env` and fill in your values.

---

## Environment Variables

### 🔑 API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `KLING_API_KEY` | For Kling jobs | Kling AI API key for video generation |
| `DOUBAO_API_KEY` | For Doubao jobs | ByteDance Doubao API key |
| `OPENAI_API_KEY` | For OpenAI jobs | OpenAI API key (GPT-4o for video) |
| `GEMINI_API_KEY` | For Gemini jobs | Google Gemini API key |
| `VOLCENGINE_API_KEY` | Future use | Volcano Engine API key |

> **Note**: At least one API key is required for cloud-based video generation.  
> For local rendering without cloud providers, set `backend=local` and ensure FFmpeg is installed.

---

### 🔐 Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SECURITY_ENABLED` | `false` | Enable/disable HTTP Basic Auth (`true`/`false`) |
| `API_KEY_USERNAME` | `admin` | Username for API authentication |
| `API_KEY_PASSWORD` | `changeme123` | Password for API authentication |

> Local development now defaults to `SECURITY_ENABLED=false`. Enable it explicitly in production.

**Rate limits** (when `SECURITY_ENABLED=true`):
- 10 requests per minute per user
- 100 requests per hour per user

---

### 🖥️ Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host to bind the server to |
| `PORT` | `8000` | Port to bind the server to |
| `DEBUG` | `false` | Enable debug mode for development |

---

### 📁 Directory Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `uploads` | Directory for uploaded images and job files |
| `OUTPUT_DIR` | `outputs` | Directory for generated video files |
| `DATA_DIR` | `.data` | Directory for job records and asset index |

> **Docker**: These directories are automatically created inside the container.  
> Mount them as volumes to persist data between restarts (see [DEPLOYMENT.md](./DEPLOYMENT.md)).

---

## Complete `.env` Example

```env
# ===========================================
# Pet Anime Video - Configuration
# ===========================================

# ---- API Keys ----
# Get your API keys from the respective provider dashboards

KLING_API_KEY=kl_xxxxxxxxxxxxxxxxxxxx
DOUBAO_API_KEY=dp_xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIza_xxxxxxxxxxxxxxxxxxxx
VOLCENGINE_API_KEY=

# ---- Security ----
# Set to "false" to disable authentication (local development only!)
SECURITY_ENABLED=false

# Change these in production!
API_KEY_USERNAME=admin
API_KEY_PASSWORD=changeme123

# ---- Server ----
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ---- Directories ----
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
DATA_DIR=.data

# ---- Python ----
PYTHONUNBUFFERED=1
```

---

## Configuration Precedence

Values are loaded in this order (later overrides earlier):

1. **Defaults** — hardcoded in `backend/app/config.py`
2. **Environment variables** — system environment
3. **`.env` file** — project-level overrides (highest priority)

---

## Storyboard Encoding Options

These can also be set via `storyboard_json` in the API request:

| Field | Default | Range | Description |
|-------|---------|-------|-------------|
| `x264_preset` | `veryfast` | ultrafast → veryfast → slow | FFmpeg encoding speed. Slower = smaller file but takes longer |
| `x264_crf` | `26` | 16–34 | Quality (16=best, 34=worst) |
| `x264_tune` | `stillimage` | - | FFmpeg x264 tune parameter |

**Encoding Presets Comparison**:

| Preset | Speed | Output Size | Use Case |
|--------|-------|-------------|----------|
| `ultrafast` | Fastest | Largest | Real-time preview |
| `veryfast` | Very fast | Medium | **Recommended (default)** |
| `fast` | Fast | Medium-small | Batch processing |
| `medium` | Medium | Small | Balanced production |
| `slow` | Slow | Smallest | Archival quality |

---

## Docker Environment Variables

When using `docker-compose`, set API keys in your shell or a `.env` file:

```bash
# Set API keys before running docker-compose
export KLING_API_KEY=kl_your_key_here
export DOUBAO_API_KEY=dp_your_key_here

# Start services
docker-compose up -d
```

Or create a `backend/.env` file and mount it (already configured in `docker-compose.yml`):

```yaml
volumes:
  - ./backend/.env:/app/.env:ro
```

---

## Provider Configuration

Each AI provider must be explicitly configured with its API key to be usable. Set `KLING_API_KEY` to enable Kling, `DOUBAO_API_KEY` for Doubao, etc.

**Provider selection** is done at job creation time via the `provider` field:
- `kling` — Kling AI (default)
- `openai` — OpenAI GPT-4o
- `gemini` — Google Gemini
- `doubao` — ByteDance Doubao

The `backend` field controls whether to use cloud APIs or local FFmpeg rendering:
- `auto` — use cloud if API key available, fall back to local
- `cloud` — only use cloud provider APIs
- `local` — only use local FFmpeg rendering (requires no API keys)

---

## Health Checks

The Docker healthcheck verifies the service is responding:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```
