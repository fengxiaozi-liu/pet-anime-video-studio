# 🚀 Quick Start Guide - Pet Anime Video Generator

Create anime-style videos from your pet photos in minutes!

## ⚡ Super Fast Setup (5 minutes)

### Prerequisites

- Docker & Docker Compose (version 20.10+)
- Python 3.10+ (for local development)

### Option A: Docker (Recommended for Production)

```bash
cd pet-anime-video

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Access API at http://localhost:8000
curl http://localhost:8000/docs
```

### Option B: Local Development

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📹 Creating Your First Video

### Step 1: Prepare Images

You need at least 1 image of your pet (recommended: 20+ for best results).

```bash
# Example images directory
mkdir /tmp/my-cat-videos
cp cat*.jpg /tmp/my-cat-videos/
```

### Step 2: Generate Video

Using the API (API docs at `http://localhost:8000/docs`):

```python
import requests

response = requests.post(
    "http://localhost:8000/api/jobs",
    json={
        "backend": "local",
        "prompt": "A cute orange cat playing with yarn in a cozy living room",
        "images": ["/tmp/my-cat-videos/cat1.jpg", "/tmp/my-cat-videos/cat2.jpg"],
        "duration_s": 15,
        "template_name": "douyin",
        "bgm": None,  # Optional: path to MP3 file
    }
)

job_id = response.json()["job_id"]
print(f"Job created: {job_id}")
```

### Step 3: Check Status

```python
# Poll job status
while True:
    status = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
    data = status.json()
    
    print(f"Status: {data['status']}, Stage: {data['stage']}")
    
    if data["status"] == "done":
        print(f"✅ Video ready: {data['output']}")
        break
    elif data["status"] == "failed":
        print(f"❌ Failed: {data.get('status_text', 'Unknown error')}")
        break
    
    import time
    time.sleep(5)
```

## 🎨 Template Options

| Template | Aspect Ratio | Platform | Duration |
|----------|-------------|----------|----------|
| `douyin` | 720x1280 | TikTok/Douyin | ~15s |
| `instagram_reels` | 720x1280 | Instagram | ~15s |
| `tiktok` | 720x1280 | TikTok | ~15s |
| `xiaohongshu` | 720x1280 | Xiaohongshu | ~15s |
| `custom` | Any | Custom | Flexible |

## 🔧 Configuration

Edit `.env` or pass environment variables:

```bash
# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
PYTHONPATH=.

# Cloud Providers (optional)
KLING_API_KEY=your_kling_api_key
OPENAI_API_KEY=your_openai_api_key
MINIMAX_API_KEY=your_minimax_api_key

# Storage
DATA_DIR=/app/data
OUTPUT_DIR=/app/output
```

## 🧪 Testing

Run the test suite:

```bash
cd backend
pytest tests/ -v

# With coverage report
pytest --cov=app --cov-report=html
```

## 🐛 Troubleshooting

### Docker won't start

```bash
# Check if ports are in use
lsof -i :8000  # Kill process if needed

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Images not found

Make sure image paths are absolute and accessible to the container:

```python
# ❌ Wrong (relative path inside container)
"images": ["cat1.jpg"]

# ✅ Correct (mounted volume path)
"images": ["/app/images/cat1.jpg"]
```

### Local render fails

Ensure FFmpeg is available:

```bash
# In Docker container
docker-compose exec backend which ffmpeg

# Or install locally
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS
```

## 📖 API Reference

Full API documentation available at: **http://localhost:8000/docs**

Main endpoints:
- `POST /api/jobs` - Create new video job
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs/recent` - List recent jobs
- `GET /health` - Health check

## 🆘 Need Help?

- Issues: GitHub repository issues tab
- Discord: Join our community channel
- Email: support@petanime.video

---

**Made with ❤️ for pet lovers everywhere!** 🐱🐶
