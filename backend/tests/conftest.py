"""Pytest configuration and common fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import pytest

# Add parent directory to path so we can import app modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Disable colored output for CI compatibility
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


@pytest.fixture(scope="session")
def project_root():
    """Return the project root path."""
    return PROJECT_ROOT


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    
    # Cleanup after test (optional - comment out for debugging)
    import shutil
    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def sample_storyboard():
    """Provide a sample storyboard for testing."""
    from app.schema import Storyboard
    
    return Storyboard(
        width=720,
        height=1280,
        fps=30,
        platform="douyin",
        scenes=[],
        subtitles=True,
        bgm_volume=0.5,
    )


@pytest.fixture
def sample_scene():
    """Provide a sample scene for testing."""
    from app.schema import Scene
    
    return Scene(
        image_paths=["sample_image.png"],
        duration_s=5.0,
        prompt="A cute cat playing in the garden",
        subtitles=[
            {"text": "Hello!", "start_t": 0.0, "end_t": 2.0},
            {"text": "Goodbye!", "start_t": 3.0, "end_t": 5.0},
        ],
    )


@pytest.fixture
def mock_job_data(temp_dir):
    """Provide sample job data structure."""
    output_path = temp_dir / "output.mp4"
    return {
        "job_id": "test-job-123",
        "backend": "local",
        "provider": None,
        "prompt": "Test video generation",
        "storyboard": {
            "width": 720,
            "height": 1280,
            "fps": 30,
            "platform": "douyin",
        },
        "images": [str(temp_dir / "frame1.png"), str(temp_dir / "frame2.png")],
        "bgm": None,
        "template_name": "default",
        "output": str(output_path),
    }
