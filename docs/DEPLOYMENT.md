# Deployment Guide - Pet Anime Video

This guide covers production deployment options for Pet Anime Video.

---

## Prerequisites

- Docker & Docker Compose
- At least one AI provider API key (Kling, OpenAI, Gemini, or Doubao)
- 2GB+ RAM available for the container
- FFmpeg (for local rendering fallback — bundled in Docker image)

---

## Option 1: Docker Compose (Recommended)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/ferryman-lab/pet-anime-video.git
cd pet-anime-video

# 2. Configure environment
cp .env.example backend/.env
# Edit backend/.env with your API keys

# 3. Build and start
docker-compose up -d --build

# 4. Verify it's running
curl http://localhost:8000/health
```

### Set API Keys

Edit `backend/.env`:

```env
KLING_API_KEY=kl_your_kling_key_here
DOUBAO_API_KEY=dp_your_doubao_key_here
OPENAI_API_KEY=sk_your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

Or pass them at runtime:

```bash
KLING_API_KEY=xxx DOUBAO_API_KEY=yyy docker-compose up -d
```

### Volume Mounts

Data persists in these directories on the host:

| Host Path | Container Path | Contents |
|-----------|---------------|----------|
| `./backend/uploads` | `/app/uploads` | Uploaded images, job files |
| `./backend/outputs` | `/app/outputs` | Generated videos |
| `./backend/.data` | `/app/.data` | Job records, asset index |

> **Important**: Never delete these directories — they contain your job history and outputs.

### Useful Commands

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down

# Full rebuild
docker-compose down && docker-compose up -d --build
```

---

## Option 2: Systemd Service (Linux)

For production servers running on bare metal or VMs.

### 1. Build the Docker image

```bash
cd /opt/pet-anime-video
git pull
docker-compose build
```

### 2. Install the systemd service

Copy `systemd/pet-anime-video.service` (edit paths first):

```ini
[Unit]
Description=Pet Anime Video Backend
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/pet-anime-video
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp systemd/pet-anime-video.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pet-anime-video
sudo systemctl start pet-anime-video
```

### 3. Verify

```bash
sudo systemctl status pet-anime-video
curl http://localhost:8000/health
```

---

## Option 3: OpenClaw Cron (Automated)

If you have OpenClaw installed, use the included cron workflow for scheduled automation.

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video
bash scripts/cron-setup.sh
```

See [CRON_SETUP.md](../CRON_SETUP.md) for full details.

---

## Production Hardening

### Change Default Credentials

```env
API_KEY_USERNAME=your_secure_username
API_KEY_PASSWORD=your_very_strong_password
SECURITY_ENABLED=true
```

### Use a Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100M;  # Allow large uploads
    }
}
```

### Resource Limits

The `docker-compose.yml` includes sensible defaults:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

Adjust based on your workload. More images per job or longer videos need more memory.

### Firewall

Only expose port 8000 to necessary networks:

```bash
# Allow only from internal network
ufw allow from 192.168.1.0/24 to any port 8000

# Or disable direct access, use nginx/Cloudflare tunnel
ufw deny 8000
```

### Environment File Security

```bash
# Make .env readable only by owner
chmod 600 backend/.env
```

---

## Backend Scaling

### Multiple Replicas

For high availability, run behind a load balancer:

```yaml
services:
  pet-anime-video:
    # ... existing config ...
    deploy:
      replicas: 2
```

> **Note**: Jobs are stored in a local JSON file (`jobs.json`). Multiple replicas will **not** share job state unless you migrate to a shared database (Redis, PostgreSQL).

### Shared Job Store (Future)

To support multi-replica deployments, replace the JSON file store in `backend/app/jobs.py` with a Redis-backed or PostgreSQL-backed store.

---

## Backup

### Job Data

```bash
# Backup everything
tar -czf pet-anime-video-backup-$(date +%Y%m%d).tar.gz \
  backend/uploads \
  backend/outputs \
  backend/.data \
  backend/.env
```

### Automated Backups with Cron

```bash
# Add to crontab
0 3 * * * tar -czf /backups/pet-anime-$(date +\%Y\%m\%d).tar.gz \
  /opt/pet-anime-video/backend/uploads \
  /opt/pet-anime-video/backend/outputs \
  /opt/pet-anime-video/backend/.data

# Keep last 7 days
0 4 * * * find /backups -name "pet-anime-*.tar.gz" -mtime +7 -delete
```

---

## Monitoring

### Health Check

```bash
# Simple monitoring script
while true; do
  if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ Healthy"
  else
    echo "✗ Unhealthy - restarting"
    docker-compose restart
  fi
  sleep 30
done
```

### Log Aggregation

```bash
# View last 100 lines of logs
docker-compose logs --tail=100

# Search for errors
docker-compose logs | grep -i error

# Follow logs in real time
docker-compose logs -f backend
```

---

## Directory Structure After Deployment

```
pet-anime-video/
├── backend/
│   ├── .env              # ⚠️ Your secrets — never commit this
│   ├── uploads/          # Uploaded images (persisted)
│   ├── outputs/          # Generated videos (persisted)
│   ├── .data/            # Job records & asset index (persisted)
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── API.md
│   ├── CONFIGURATION.md
│   └── DEPLOYMENT.md
└── static/
    └── templates/
```

---

## Uninstallation

```bash
# Stop containers
docker-compose down

# Remove images (optional)
docker-compose down --rmi all

# Remove data volumes (⚠️ destroys all jobs and videos)
docker-compose down -v

# Remove the project directory
cd ..
rm -rf pet-anime-video
```

> **Warning**: `-v` deletes all persisted data. Make sure you have backups before running this.
