# Backend Tests

## Quick Start

```bash
cd backend

# Option 1: Use the test runner script (recommended)
./run-tests.sh

# Option 2: Run pytest directly
pytest tests/ -v

# Option 3: Run with coverage report
pytest --cov=app --cov-report=html
```

## Test Files

| File | Description | Count |
|------|-------------|-------|
| `test_jobs.py` | JobStore CRUD operations | 12 tests |
| `test_assets.py` | AssetStore file management | 10 tests |
| `test_schema.py` | Storyboard & Scene models | 16 tests |
| `test_pipeline.py` | Job execution flow | 10 tests |
| `conftest.py` | Shared fixtures | N/A |

**Total**: 48 unit tests

## Examples

### Run specific test file
```bash
pytest tests/test_jobs.py -v
```

### Run specific test function
```bash
pytest tests/test_jobs.py::TestJobStore::test_create_job_success -v
```

### Run only fast tests (exclude slow integration tests)
```bash
pytest -m "not integration" -v
```

### Generate coverage HTML report
```bash
pytest --cov=app --cov-report=html:htmlcov
open htmlcov/index.html
```

## Writing New Tests

Template for new test classes:

```python
"""Unit tests for <module_name>.py."""
from __future__ import annotations
import pytest
from app.<module> import ClassName


class TestClassName:
    """Test ClassName functionality."""

    def setup_method(self):
        """Setup before each test."""
        pass

    def test_example(self):
        """Test description."""
        # Arrange
        obj = ClassName()
        
        # Act
        result = obj.method()
        
        # Assert
        assert result is not None
```

## CI Integration

Tests are designed to run in GitHub Actions:

```yaml
- name: Run tests
  run: |
    cd backend
    pip install pytest pytest-cov
    pytest tests/ --cov=app --cov-report=term-missing
```

## Troubleshooting

### Import Errors
```bash
# Ensure PYTHONPATH includes current directory
export PYTHONPATH=.
pytest tests/
```

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-cov
```

### Flaky Tests
If tests fail intermittently, add retry logic or mock external dependencies better.
