# Troubleshooting Guide

Common issues and their solutions for Pet Anime Video Generator.

## Installation Issues

### Docker Won't Start

**Symptoms**: Container exits immediately or shows errors

**Solutions**:

1. **Check port conflicts**
   ```bash
   # Check if port 8000 is in use
   lsof -i :8000
   
   # Kill conflicting process (replace PID)
   kill -9 <PID>
   ```

2. **Rebuild from scratch**
   ```bash
   docker-compose down -v  # Remove volumes too
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **Check disk space**
   ```bash
   df -h /app  # Ensure at least 5GB free
   ```

4. **View container logs**
   ```bash
   docker-compose logs backend | tail -50
   ```

### Python Dependencies Fail

**Symptoms**: `pip install` errors, missing modules

**Solutions**:

```bash
# Upgrade pip first
python3 -m pip install --upgrade pip setuptools wheel

# Install requirements with verbose output
pip install -r requirements.txt -v

# If specific package fails, try installing individually
pip install pydantic fastapi uvicorn
```

## Runtime Errors

### Images Not Found

**Symptoms**: `FileNotFoundError`, "images empty" errors

**Root Cause**: Container can't access host file paths

**Solutions**:

1. **Use mounted volumes** (in `docker-compose.yml`)
   ```yaml
   volumes:
     - ./images:/app/images
     - ./output:/app/output
   ```

2. **Use absolute paths in API calls**
   ```python
   # ✅ Correct
   {
       "images": [
           "/app/images/cat1.jpg",
           "/app/images/cat2.jpg"
       ]
   }
   
   # ❌ Wrong
   {
       "images": ["cat1.jpg"]  # Relative path won't work
   }
   ```

### Local Render Fails

**Symptoms**: FFmpeg errors, corrupted output

**Solutions**:

```bash
# Inside container
docker-compose exec backend which ffmpeg
ffmpeg -version

# Test basic FFmpeg command
docker-compose exec backend ffmpeg -f lavfi -i testsrc=size=192x108:rate=1 \
    -frames:v 10 /tmp/test.mp4

# Verify output
ls -lh /tmp/test.mp4
```

### Cloud Provider API Errors

**Symptoms**: 401 Unauthorized, 429 Rate Limit, timeout

**Solutions**:

1. **Check API keys**
   ```bash
   # Environment variables must be set
   echo $KLING_API_KEY
   echo $OPENAI_API_KEY
   ```

2. **Verify provider availability**
   ```python
   # Test connection
   import requests
   response = requests.get("https://api.klingai.com/v1/health")
   print(response.status_code)
   ```

3. **Implement retry logic**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
   def call_api():
       # Your API call here
       pass
   ```

## Performance Issues

### Slow Video Generation

**Factors**:
- Number of images (more = slower)
- Duration (longer = more scenes)
- Backend type (local vs cloud)

**Optimizations**:

```python
# Reduce image count
{
    "images": selected_top_20(images),  # Instead of all 100
    "duration_s": 10,  # Shorter video
    "scenes_per_image": 1,  # Fewer scenes per image
}
```

### High Memory Usage

**Symptoms**: OOM errors, container restarts

**Solutions**:

```yaml
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### Disk Space Running Low

**Cleanup commands**:

```bash
# Clean old Docker images
docker image prune -a

# Remove completed jobs' temporary files
rm -rf /app/data/temp/*

# Archive old videos
tar -czf old_videos.tar.gz /app/output/*.mp4
```

## Advanced Debugging

### Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

### Inspect Job State

```python
# Direct database inspection
import json
with open("/app/jobs.json") as f:
    jobs = json.load(f)
    
for job_id, data in list(jobs.items())[:3]:
    print(f"{job_id}: {data['status']} - {data['stage']}")
```

### Test Pipeline Manually

```python
from app.jobs import JobStore
from app.pipeline import run_local_render

store = JobStore("/app/jobs.json")
job = store.get("your-job-id")

# Run render step directly
run_local_render(job)
```

## Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| WebP images sometimes fail | 🟡 In progress | Convert to PNG first |
| Very long videos (>60s) may have audio sync drift | 🟡 In progress | Keep videos under 30s |
| Some providers rate-limit aggressively | 🟢 Documented | Use `backend="auto"` for fallback |

## Getting Help

If you've tried everything above and still stuck:

1. **Gather information**
   ```bash
   # System info
   uname -a
   docker --version
   python3 --version
   
   # Container info
   docker-compose ps
   docker-compose logs --tail=100 backend
   
   # Job details (if applicable)
   curl http://localhost:8000/api/jobs/YOUR_JOB_ID
   ```

2. **Create issue with**:
   - Steps to reproduce
   - Error messages (full stack trace)
   - Configuration used (sanitized)
   - Version info from above

3. **Contact channels**:
   - GitHub Issues: https://github.com/pet-anime-video/issues
   - Discord: Join our community
   - Email: support@petanime.video (business hours only)
