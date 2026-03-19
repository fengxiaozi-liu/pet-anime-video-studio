# 🐱 Pet Anime Video - AI-Powered Video Generation Platform

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Project Status**: Under Active Development  
> **Latest Update**: 2026-03-19  
> **Automated Optimization**: ✅ Enabled (Daily at 9:00 AM)

---

## 📖 Overview

Pet Anime Video is a production-ready platform that transforms pet photos into stylized anime videos using AI models. The project includes:

- **Backend**: FastAPI microservice with job management and pipeline orchestration
- **Frontend**: Vue.js SPA with drag-and-drop interface
- **AI Pipeline**: Integration with Kling, RunPod, and other video generation APIs
- **Automated Workflow**: Smart agent-based optimization system

## ✨ Features

- 🎨 Multiple video generation models support
- ⚡ Async task processing with Redis queue
- 📊 Real-time progress tracking
- 🔒 Secure API key management
- 🐳 Docker-ready deployment
- 🤖 Automated code quality improvement
- 📱 Mobile-responsive UI

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/ferryman-lab/pet-anime-video.git
cd pet-anime-video

# Install Python dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit .env with your API keys

# Run backend server
python backend/main.py

# Visit http://localhost:8000
```

### Docker Deployment

The fastest way to deploy Pet Anime Video is using Docker Compose:

```bash
# 1. Clone repository and navigate to project
git clone https://github.com/ferryman-lab/pet-anime-video.git
cd pet-anime-video

# 2. Configure environment variables
cp backend/.env.example backend/.env
# Edit .env with your API keys:
#   KLING_API_KEY=your_kling_api_key
#   XINGHUN_API_KEY=your_xinghun_api_key

# 3. Build and start containers
docker-compose up -d --build

# 4. View logs
docker-compose logs -f

# 5. Stop services
docker-compose down
```

**Quick Commands:**

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start in background |
| `docker-compose down` | Stop and remove containers |
| `docker-compose logs -f` | Follow logs |
| `docker-compose restart` | Restart services |
| `docker-compose ps` | Check status |

**Directory Persistence:**

Your data is safely persisted in these directories:
- `backend/uploads/` - Uploaded images and assets
- `backend/outputs/` - Generated videos
- `backend/data/` - Job records and asset indices

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for advanced configuration.

## 🛠️ Automation System

### 🤖 Automated Optimization Workflow

The project includes an intelligent workflow agent that automatically improves the codebase every day!

**What it does:**
- Runs daily at 9:00 AM
- Executes pending optimization tasks in priority order
- Uses specialized AI agents for different types of improvements
- Tracks progress and logs all activities

**Setup (one-time):**

```bash
cd /home/fengxiaozi/.openclaw/workspace/pet-anime-video
bash scripts/cron-setup.sh
```

**Monitor progress:**

```bash
# View current status
python scripts/workflow-agent.py --status

# Interactive dashboard
bash scripts/dashboard.sh

# Watch logs live
tail -f logs/workflow.log
```

**Current Tasks:**

| Task | Status | Description |
|------|--------|-------------|
| Config Management | ✅ Completed | API key management & env handling |
| Docker Setup | ⏳ Pending | Production Dockerfile & compose |
| Unit Tests | ⏳ Pending | pytest framework & coverage |
| Documentation | ⏳ Pending | API reference & guides |
| UI Improvements | ⏳ Pending | Responsive design & UX |
| Code Quality | ⏳ Pending | Type hints & linting |

Learn more: [Auto Workflow Guide](./AUTO_WORKFLOW_README.md)

## 📁 Project Structure

```
pet-anime-video/
├── backend/                 # FastAPI backend service
│   ├── app/
│   │   ├── main.py         # API endpoints
│   │   ├── config.py       # Configuration management
│   │   ├── jobs.py         # Job store & management
│   │   └── pipeline.py     # Video generation pipeline
│   ├── tests/              # Unit tests
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/               # Vue.js frontend application
│   ├── src/
│   │   ├── components/     # Vue components
│   │   ├── api/           # API client
│   │   └── styles/        # CSS stylesheets
│   └── package.json       # NPM dependencies
├── scripts/                # Utility scripts
│   ├── workflow-agent.py  # Main workflow orchestrator
│   ├── scheduled-workflow.py  # Cron job runner
│   └── dashboard.sh       # Interactive dashboard
├── docs/                   # Documentation
│   ├── API.md             # REST API reference
│   ├── DEPLOYMENT.md      # Deployment guide
│   └── CONTRIBUTING.md    # Contribution guidelines
├── logs/                   # Runtime logs
├── systemd/               # Systemd service files
├── WORKFLOW.md            # Workflow agent documentation
├── AUTO_WORKFLOW_README.md  # Quick start guide
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

Create `backend/.env` from the example template:

```bash
cp backend/.env.example backend/.env
```

Required variables:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# API Keys
KUNGFU_AI_KEY=your_kungfu_key
KUNG_SHAN_API_KEY=your_kungshan_key

# Database (JSON File Storage)
JOB_STORE_PATH=/data/jobs.json
```

Full configuration reference: [Config Documentation](./backend/README.md)

## 🧪 Testing

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend/app --cov-report=html

# Linting
flake8 backend/app
black --check backend/app
```

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guidelines](./docs/CONTRIBUTING.md) before submitting PRs.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- [API Reference](./docs/API.md) - Complete REST API documentation
- [Deployment Guide](./docs/DEPLOYMENT.md) - Production deployment instructions
- [Contributing Guide](./docs/CONTRIBUTING.md) - How to contribute
- [Workflow Agent](./WORKFLOW.md) - Automated optimization system
- [Audit Report](./AUDIT_REPORT.md) - Project health assessment

## 🛡️ Security

- API keys are securely managed through environment variables
- Input validation on all user-facing endpoints
- Rate limiting enabled (coming soon)
- CORS properly configured

Report security vulnerabilities to security@ferryman.lab

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Developer**: ferryman
- **AI Assistant**: Trigger (OpenClaw)

## 🙏 Acknowledgments

- [Kling AI](https://kling.ai) for video generation capabilities
- [RunPod](https://runpod.io) for cloud GPU infrastructure
- All contributors who have helped improve this project

## 📞 Support

- **Documentation**: See the [docs/](./docs/) folder
- **Issues**: [GitHub Issues](https://github.com/ferryman-lab/pet-anime-video/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ferryman-lab/pet-anime-video/discussions)

---

**Made with ❤️ by Ferryman Lab**

*Transforming pet photos into beautiful anime adventures!*
