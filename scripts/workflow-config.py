#!/usr/bin/env python3
"""
Pet Anime Video - Workflow Task Configuration

This module provides task definitions for the automated optimization workflow.
Used by OpenClaw heartbeat mechanism to spawn appropriate sub-agents.
"""

TASKS = {
    "docker-setup": {
        "priority": 1,
        "title": "Docker Deployment Setup",
        "description": """
# Docker Setup Task for Pet Anime Video Project

## Objective
Create production-ready containerization support for the pet-anime-video project.

## Deliverables

### 1. Backend Dockerfile
Location: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/backend/Dockerfile`

Requirements:
- Use Python 3.10-slim base image
- Multi-stage build for smaller final image
- Proper layer caching (copy requirements.txt first)
- Install dependencies with pip cache
- Non-root user for security
- Health check endpoint: /health
- Environment variable support via .env file

### 2. Docker Compose
Location: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/docker-compose.yml`

Services to define:
- backend: FastAPI service on port 8000
- nginx: Reverse proxy (optional, can skip for MVP)
- redis: For future async task queue (optional)

Features:
- Development mode (DEBUG=true, hot reload)
- Production mode (DEBUG=false, gunicorn)
- Volume mounts for persistent data
- Environment variables from .env file
- Health checks for all services

### 3. Docker Ignore
Location: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/.dockerignore`

Exclude:
- __pycache__, *.pyc
- .git, .env.local
- tests/, logs/
- *.md (except README)
- venv/, .venv/

### 4. Documentation Updates
Update README.md with:
- Docker Quick Start section
- docker-compose up commands
- Environment variable reference
- Troubleshooting tips

## Constraints
- Final image size < 500MB if possible
- No hardcoded secrets in Dockerfile
- Follow Python and Docker best practices
- Support both ARM64 and AMD64 architectures

## Success Criteria
✅ Can run `docker-compose up -d` and access http://localhost:8000
✅ Health endpoint returns 200 OK
✅ All environment variables properly configured
✅ Build completes in < 5 minutes on typical hardware

## Testing Commands
```bash
docker-compose build
docker-compose up -d
curl http://localhost:8000/health
docker-compose down
```

## Reference Links
- Official Python Docker images: https://hub.docker.com/_/python
- FastAPI deployment guide: https://fastapi.tiangolo.com/deployment/
- Docker best practices: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
"""
    },
    
    "unit-tests": {
        "priority": 2,
        "title": "Unit Test Implementation",
        "description": """
# Unit Testing Task for Pet Anime Video Project

## Objective
Implement comprehensive unit test suite with 70%+ code coverage.

## Priority Test Targets

### 1. Job Store (`backend/app/jobs.py`)
Test file: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/backend/tests/test_jobs.py`

Test cases:
- Create job with valid parameters
- Get existing job by ID
- Update job status and metadata
- Delete job cleanup
- List jobs filtering (by status, date range)
- Invalid job ID handling
- Concurrent access scenarios

### 2. Pipeline Logic (`backend/app/pipeline.py`)
Test file: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/backend/tests/test_pipeline.py`

Test cases:
- Task flow orchestration
- Error handling for failed steps
- Retry logic verification
- Mock external API calls (kling, runpod)
- Progress tracking accuracy

### 3. API Endpoints (`backend/app/main.py`)
Test file: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/backend/tests/test_main.py`

Test cases:
- POST /upload - File validation
- GET /jobs/<id> - Response format
- GET /health - Service health check
- Authentication requirements
- Rate limiting behavior

### 4. Configuration (`backend/app/config.py`)
Test file: `/home/fengxiaozi/.openclaw/workspace/pet-anime-video/backend/tests/test_config.py`

Test cases:
- Environment variable loading
- Missing required variables error
- Default value fallbacks
- Type coercion (bool, int, str)
- Validation of API key formats

## Requirements
- Framework: pytest
- Coverage target: 70% minimum on core modules
- External API mocking: pytest-mock
- Deterministic tests (no randomness)
- Fast execution (< 30 seconds total)

## Project Structure
```
backend/tests/
├── conftest.py          # Shared fixtures
├── test_jobs.py         # JobStore tests
├── test_pipeline.py     # Pipeline logic tests
├── test_main.py         # API endpoint tests
└── test_config.py       # Configuration tests
```

## Configuration Files

### pytest.ini
```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=backend/app --cov-report=html
```

### pyproject.toml (tool sections)
Add pytest configuration under `[tool.pytest.ini_options]`

## Success Criteria
✅ All tests pass with `pytest backend/tests/ -v`
✅ Coverage report shows >70% for backend/app/
✅ No actual API calls to external services
✅ Tests are deterministic and repeatable
✅ CI-ready (can run in GitHub Actions)

## Running Tests
```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend/app --cov-report=term-missing

# Run specific test file
pytest backend/tests/test_jobs.py -v

# Generate HTML coverage report
pytest backend/tests/ --cov=backend/app --cov-report=html
open htmlcov/index.html
```

## Mocking Guidelines
- Use `@pytest.fixture` for reusable mocks
- Mock at the boundary (don't mock internal methods)
- Use `unittest.mock.patch` for context managers
- Keep mocks isolated per test function
"""
    },
    
    "docs-improve": {
        "priority": 3,
        "title": "Documentation Enhancement",
        "description": """
# Documentation Improvement Task

## Objective
Create comprehensive documentation to make the project production-ready.

## Required Documents

### 1. API Reference (docs/API.md)
Content:
- Complete REST API endpoint listing
- Request/response schemas for each endpoint
- Authentication requirements
- Error codes and descriptions
- Example curl commands
- Rate limiting information
- Webhook events (if any)

Structure:
```markdown
# API Reference

## Authentication
...

## Endpoints
### POST /upload
#### Request
...

#### Response
...

#### Examples
...
```

### 2. Deployment Guide (docs/DEPLOYMENT.md)
Content:
- Local development setup (5-minute quick start)
- Environment variables reference (complete table)
- Docker deployment instructions
- Production deployment checklist
- Scaling considerations
- Backup and restore procedures
- Troubleshooting common issues

Sections:
1. Prerequisites
2. Installation Options (Source vs Docker)
3. Configuration
4. Running Locally
5. Production Deployment
6. Monitoring & Logging
7. Troubleshooting

### 3. Contributing Guide (docs/CONTRIBUTING.md)
Content:
- Code style guidelines (PEP 8, formatting)
- Git commit message format (conventional commits)
- Pull request process
- Branch naming conventions
- Testing requirements
- Review process
- Release workflow

Include templates for:
- Commit messages
- Pull request descriptions
- Issue reports

### 4. Enhanced README.md
Updates needed:
- Add "Quick Start" section (setup in 5 minutes)
- Improve installation instructions with step-by-step commands
- Add example usage with code snippets
- Include screenshots/GIFs of the UI
- Environment configuration examples
- Link to other documentation files
- Add badges (build status, coverage, etc.)

## Deliverables
- `/docs/API.md` - Full API documentation
- `/docs/DEPLOYMENT.md` - Comprehensive deployment guide
- `/docs/CONTRIBUTING.md` - Contribution guidelines
- Updated `/README.md` - Enhanced project overview
- Table of contents in README linking to all docs

## Writing Standards
- Use clear, concise language
- Assume minimal prior knowledge
- Include practical, copy-pasteable examples
- Use consistent formatting across all docs
- Add code blocks with syntax highlighting
- Cross-link related topics

## Success Criteria
✅ New developer can set up locally in < 15 minutes following docs
✅ All API endpoints documented with examples
✅ Deployment guide covers both dev and prod scenarios
✅ Contributing guide reduces PR review friction
✅ No broken links or outdated information

## Documentation Checklist
Before marking complete:
- [ ] Spell-check all documents
- [ ] Verify all code examples work
- [ ] Test all commands in fresh environment
- [ ] Check markdown rendering
- [ ] Validate all links
- [ ] Ensure consistent terminology
"""
    },
    
    "ui-improve": {
        "priority": 4,
        "title": "Frontend UX Improvements",
        "description": """
# Frontend User Experience Enhancement Task

## Objective
Improve the frontend UI/UX for better usability and mobile compatibility.

## Required Improvements

### 1. Responsive Design (Mobile-First)
Files to modify:
- `/frontend/src/styles/main.css`
- `/templates/index.html` (or relevant template files)

Requirements:
- Mobile-first responsive breakpoints
- Touch-friendly button sizes (min 44px)
- Optimized image display on small screens
- Flexible grid system using CSS Grid/Flexbox
- Hide non-essential elements on mobile
- Hamburger menu for navigation on small screens

Breakpoints:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### 2. Drag & Drop File Upload
Implementation:
- Native HTML5 drag-and-drop API
- Visual feedback during drag operations
- Multi-file upload support
- File type validation before upload
- File size limits enforcement
- Cancel upload functionality

Visual states:
- Idle state (dropzone visible)
- Drag-over state (highlighted border)
- Uploading state (progress indicator)
- Success state (checkmark)
- Error state (error message)

### 3. Progress Visualization
Features to add:
- Real-time progress bar with percentage
- Step-by-step pipeline visualization
- Current stage indicator
- Estimated time remaining (if calculable)
- Success/failure states with icons
- Retry button for failed tasks

UI components:
```
[✓] Image Uploaded
[→] Processing... ████░░░░ 40%
[ ] Style Transfer
[ ] Video Generation
[ ] Ready
```

### 4. Error Handling Improvements
Implement:
- Friendly, user-facing error messages
- Helpful troubleshooting suggestions
- Non-blocking error toasts/notifications
- Form validation with inline feedback
- Network error recovery options

Error categories:
- Validation errors (file type, size)
- API errors (service unavailable)
- Network errors (connection lost)
- Server errors (internal error)

### 5. Visual Polish
Enhancements:
- Loading animations/skeleton screens
- Consistent color scheme throughout
- Improved spacing and typography
- Consider dark mode toggle (optional)
- Smooth transitions and hover states
- Professional icon set (Font Awesome or similar)

Color palette suggestion:
- Primary: #6366f1 (indigo)
- Success: #10b981 (green)
- Warning: #f59e0b (amber)
- Error: #ef4444 (red)
- Background: #ffffff / #f9fafb

## Deliverables
- Updated HTML template files in `/templates/`
- Enhanced CSS stylesheets in `/static/css/` or `/frontend/src/styles/`
- Improved JavaScript scripts in `/static/js/` or `/frontend/src/`
- Before/after comparison screenshots
- Mobile responsiveness testing results

## Testing Requirements
- Chrome (Desktop & Mobile)
- Firefox (Desktop)
- Safari (iOS)
- Edge (Desktop)

Responsive test devices:
- iPhone SE (375px)
- iPhone 12 (390px)
- iPad (768px)
- Desktop (1920px)

## Success Criteria
✅ Passes mobile usability tests
✅ Drag-and-drop works smoothly with visual feedback
✅ Progress indicators update in real-time
✅ Error messages are helpful and actionable
✅ Consistent visual design across all pages
✅ No console errors in browser dev tools

## Accessibility (Bonus)
If time permits:
- Add ARIA labels for screen readers
- Keyboard navigation support
- Focus management for modals
- Color contrast compliance (WCAG AA)
"""
    },
    
    "code-quality": {
        "priority": 5,
        "title": "Code Quality Enhancement",
        "description": """
# Code Quality Improvement Task

## Objective
Improve overall code quality through standardization, type safety, and automation.

## Required Improvements

### 1. Type Annotations
Target: 90%+ type hint coverage across the codebase

Files to annotate (priority order):
1. `backend/app/jobs.py` - Job store functions and classes
2. `backend/app/pipeline.py` - Pipeline orchestration
3. `backend/app/main.py` - API endpoint signatures
4. `backend/app/config.py` - Configuration models

Requirements:
- Function signatures: `def func(param: type) -> return_type:`
- Class attributes with `__init__` annotations
- Use `typing` module for complex types (List, Dict, Optional, Union)
- Type aliases for repeated complex types
- Avoid `Any` unless absolutely necessary

Example:
```python
from typing import Optional, Dict, List

JobStatus = Literal["pending", "processing", "completed", "failed"]

def create_job(
    user_id: str,
    config: Dict[str, Any],
    callback_url: Optional[str] = None
) -> JobDict:
    ...
```

### 2. Logging Standardization
Replace all `print()` statements with proper logging

Configuration (`backend/app/logging_config.py`):
- Structured log format: `timestamp | level | module | message`
- Log levels: DEBUG, INFO, WARNING, ERROR
- Console output for development
- File output for production
- Log rotation (max 10MB, keep 5 files)

Usage pattern:
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing job %s", job_id)
logger.error("Failed to process job: %s", error)
```

Log locations:
- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Access logs: `logs/access.log` (for API endpoints)

### 3. Docstrings (Google Style)
Add comprehensive docstrings to:
- All public modules (module-level description)
- All classes (purpose, attributes)
- All public methods (params, returns, exceptions)
- Complex private functions

Format (Google style):
```python
def process_video(image_path: str, style: str) -> VideoResult:
    """Process an image to generate stylized video.
    
    Takes a pet photo and applies AI style transfer to create
    an anime-style video output.
    
    Args:
        image_path: Path to input image file (JPG/PNG)
        style: Style identifier (e.g., 'anime', 'realistic')
        
    Returns:
        VideoResult object containing output path and metadata
        
    Raises:
        FileNotFoundError: If image_path doesn't exist
        ValueError: If style is not recognized
        ProcessingError: If video generation fails
    """
```

### 4. Pre-commit Hooks
Setup automated code quality checks on every commit

Installation:
```bash
pip install pre-commit black isort flake8 mypy
pre-commit install
```

Configuration (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
      
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
      
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
      
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.0
    hooks:
      - id: mypy
        additional_dependencies:
          - fastapi
          - pydantic
```

Hooks to enable:
- Trailing whitespace removal
- End-of-file fixes
- YAML/JSON validation
- Black code formatting
- Isort import sorting
- Flake8 linting
- Mypy type checking

### 5. Security Hardening
Implement:

a) Rate Limiting:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/upload")
@limiter.limit("10/minute")
async def upload_file():
    ...
```

b) File Upload Validation:
- MIME type verification (not just extension)
- Maximum file size enforcement (e.g., 10MB)
- Temporary file cleanup
- Sanitize filenames

c) CORS Configuration:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

d) Input Sanitization:
- Validate all user inputs
- Escape HTML in user-generated content
- Prevent SQL injection (even with JSON storage)

## Deliverables
- Fully typed Python codebase (>90% coverage)
- Standardized logging implementation
- Comprehensive docstrings for public APIs
- `.pre-commit-config.yaml` with all hooks
- Updated `pyproject.toml` with tool configurations
- Security improvements implemented and tested

## Tool Configuration

### pyproject.toml additions
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88

[tool.flake8]
max-line-length = 88
exclude = [".git", "__pycache__", "venv"]
ignore = ["E203", "W503"]

[tool.mypy]
python_version = "3.10"
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

## Success Criteria
✅ mypy runs without errors on main code paths
✅ All print() statements replaced with logging
✅ Pre-commit hooks pass on new code
✅ Docstrings cover all public interfaces
✅ Security vulnerabilities addressed
✅ Code passes flake8 and black formatting

## Verification Commands
```bash
# Type checking
mypy backend/app/

# Formatting
black --check backend/app/
isort --check-only backend/app/

# Linting
flake8 backend/app/

# Pre-commit hooks
pre-commit run --all-files
```
"""
    }
}


def get_next_task_state(state_file: str = ".workflow-state.json") -> dict:
    """Get the next pending task from workflow state."""
    import json
    
    with open(state_file) as f:
        state = json.load(f)
    
    priority_order = ["docker-setup", "unit-tests", "docs-improve", "ui-improve", "code-quality"]
    
    for task_name in priority_order:
        if state["tasks"].get(task_name, {}).get("status") == "pending":
            task_info = TASKS.get(task_name, {})
            return {
                "task_name": task_name,
                "priority": task_info.get("priority"),
                "title": task_info.get("title"),
                "description": task_info.get("description"),
                "status": "pending"
            }
    
    return {"status": "complete", "message": "All tasks completed"}


def get_task_by_name(task_name: str) -> dict:
    """Get task details by name."""
    task_info = TASKS.get(task_name, {})
    return {
        "task_name": task_name,
        **task_info
    }


if __name__ == "__main__":
    # Test script
    print("Available tasks:")
    for name, info in TASKS.items():
        print(f"  {info['priority']}. {name}: {info['title']}")
    
    print("\n" + "="*50)
    print("Testing state checker...")
    try:
        result = get_next_task_state()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
