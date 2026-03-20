# Pet Anime Video - Backend Test Plan

## Overview

This document describes the testing strategy for the pet-anime-video backend API.

## Current Status

✅ **Unit Tests Written** (March 2026):
- `test_jobs.py` - JobStore CRUD operations
- `test_assets.py` - AssetStore file management  
- `test_schema.py` - Storyboard & Scene validation
- `test_pipeline.py` - Job execution pipeline

## How to Run Tests

```bash
cd backend

# Install dependencies if needed
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_jobs.py -v

# Run specific test function
pytest tests/test_jobs.py::TestJobStore::test_create_job_success -v

# Run only unit tests (no integration)
pytest -m "not integration"
```

## Test Structure

### Unit Tests (`tests/`)

| File | Coverage | Purpose |
|------|----------|---------|
| `test_jobs.py` | JobStore class | Test job persistence, CRUD ops, timestamps |
| `test_assets.py` | AssetStore class | Test asset file storage and indexing |
| `test_schema.py` | Storyboard, Scene models | Test validation, template application |
| `test_pipeline.py` | run_job(), render_local() | Test job execution flow (with mocks) |

### Integration Tests (Future)

These would require actual API providers or mocked servers:

- **API Endpoint Tests**: Test FastAPI routes with TestClient
- **Cloud Provider Integration**: Test actual Kling/OpenAI/minimax APIs
- **Local Render Pipeline**: Test actual video generation with FFmpeg
- **Database Migrations**: Test schema changes

## Running in CI/CD

GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=app --cov-report=term-missing
```

## Code Coverage Goals

| Module | Target | Notes |
|--------|--------|-------|
| `jobs.py` | 95% | Pure Python, easy to cover |
| `assets.py` | 90% | File I/O, needs cleanup handling |
| `schema.py` | 85% | Pydantic does most validation |
| `pipeline.py` | 70% | Complex orchestration, use mocks |
| **Overall** | **80%** | Good enough for confidence |

## Testing Checklist

Before merging PRs:

- [ ] All tests pass locally
- [ ] New code has corresponding tests
- [ ] No test flakes (consistent results)
- [ ] Coverage doesn't decrease significantly
- [ ] Integration tests updated if needed

## Mock Strategy

For cloud provider tests, use `unittest.mock.patch`:

```python
from unittest.mock import patch, MagicMock

@patch("app.pipeline.render_cloud")
def test_auto_fallback(mock_render_cloud):
    mock_render_cloud.side_effect = Exception("API down")
    # ... test fallback logic
```

## Performance Testing

Not yet implemented, but future considerations:

- Load test: 100 concurrent jobs
- Memory usage during rendering
- Disk I/O bottlenecks for large assets
