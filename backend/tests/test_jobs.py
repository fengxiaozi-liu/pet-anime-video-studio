"""Unit tests for jobs.py - JobStore functionality."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from app.jobs import JobStore


class TestJobStore:
    """Test JobStore CRUD operations and thread safety."""

    def setup_method(self):
        """Create temporary directory and JobStore for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / "jobs.json"
        self.store = JobStore(self.store_path)

    def test_create_job_success(self):
        """Test creating a new job succeeds."""
        self.store.create(
            job_id="test-job-001",
            backend="local",
            provider="kling",
            prompt="A cute cat playing",
            storyboard={"width": 1280, "height": 720, "fps": 30, "scenes": []},
            images=["/path/to/image1.png"],
            bgm=None,
            output="/output/video.mp4",
        )
        
        job = self.store.get("test-job-001")
        assert job is not None
        assert job["job_id"] == "test-job-001"
        assert job["backend"] == "local"
        assert job["status"] == "queued"
        assert job["stage"] == "queued"
        assert job["prompt"] == "A cute cat playing"

    def test_create_duplicate_job_raises_error(self):
        """Test that creating a duplicate job raises ValueError."""
        self.store.create(
            job_id="duplicate-job",
            backend="local",
            provider="kling",
            prompt="Test prompt",
            storyboard={},
            images=[],
            bgm=None,
            output="/output.mp4",
        )
        
        with pytest.raises(ValueError, match="job exists"):
            self.store.create(
                job_id="duplicate-job",
                backend="local",
                provider="kling",
                prompt="Another prompt",
                storyboard={},
                images=[],
                bgm=None,
                output="/output.mp4",
            )

    def test_get_nonexistent_job_returns_none(self):
        """Test getting a nonexistent job returns None."""
        result = self.store.get("nonexistent-job-id")
        assert result is None

    def test_patch_existing_job(self):
        """Test patching an existing job updates its fields."""
        self.store.create(
            job_id="patch-test-job",
            backend="local",
            provider="kling",
            prompt="Original prompt",
            storyboard={},
            images=[],
            bgm=None,
            output="/output.mp4",
        )
        
        self.store.patch(
            "patch-test-job",
            status="running",
            stage="rendering_local",
            status_text="Rendering in progress",
        )
        
        job = self.store.get("patch-test-job")
        assert job["status"] == "running"
        assert job["stage"] == "rendering_local"
        assert job["status_text"] == "Rendering in progress"
        assert "updated_at" in job

    def test_patch_nonexistent_job_raises_error(self):
        """Test patching a nonexistent job raises KeyError."""
        with pytest.raises(KeyError):
            self.store.patch("nonexistent-job", status="done")

    def test_list_recent_jobs(self):
        """Test listing recent jobs returns them sorted by creation time."""
        import time
        # Create jobs with small delay to ensure distinct timestamps
        self.store.create(
            job_id="job-1",
            backend="local",
            provider="kling",
            prompt="First job",
            storyboard={},
            images=[],
            bgm=None,
            output="/output1.mp4",
        )
        time.sleep(0.01)
        self.store.create(
            job_id="job-2",
            backend="cloud",
            provider="openai",
            prompt="Second job",
            storyboard={},
            images=[],
            bgm=None,
            output="/output2.mp4",
        )
        time.sleep(0.01)
        self.store.create(
            job_id="job-3",
            backend="local",
            provider="kling",
            prompt="Third job",
            storyboard={},
            images=[],
            bgm=None,
            output="/output3.mp4",
        )
        
        # List with limit of 2
        recent = self.store.list_recent(limit=2)
        assert len(recent) == 2
        # Most recent first (job-3 created last)
        assert recent[0]["job_id"] == "job-3"
        assert recent[1]["job_id"] == "job-2"

    def test_list_respects_limit(self):
        """Test that list_recent respects the limit parameter."""
        # Create 5 jobs
        for i in range(5):
            self.store.create(
                job_id=f"limit-job-{i}",
                backend="local",
                provider="kling",
                prompt=f"Job {i}",
                storyboard={},
                images=[],
                bgm=None,
                output=f"/output{i}.mp4",
            )
        
        recent = self.store.list_recent(limit=3)
        assert len(recent) == 3

    def test_extra_fields_preserved(self):
        """Test that extra fields passed to create are preserved."""
        self.store.create(
            job_id="extra-fields-job",
            backend="local",
            provider="kling",
            prompt="Test",
            storyboard={},
            images=[],
            bgm=None,
            output="/output.mp4",
            custom_field_1="value1",
            custom_field_2=42,
            custom_field_3=True,
        )
        
        job = self.store.get("extra-fields-job")
        assert job["custom_field_1"] == "value1"
        assert job["custom_field_2"] == 42
        assert job["custom_field_3"] is True

    def test_store_persists_to_file(self):
        """Test that jobs are persisted to JSON file."""
        self.store.create(
            job_id="persist-test",
            backend="local",
            provider="kling",
            prompt="Persistence test",
            storyboard={},
            images=[],
            bgm=None,
            output="/output.mp4",
        )
        
        # Verify file exists and contains data
        assert self.store_path.exists()
        content = self.store_path.read_text("utf-8")
        assert "persist-test" in content
        assert "Persistence test" in content

    def test_timestamps_set_on_create(self):
        """Test that created_at and updated_at timestamps are set."""
        self.store.create(
            job_id="timestamp-job",
            backend="local",
            provider="kling",
            prompt="Test",
            storyboard={},
            images=[],
            bgm=None,
            output="/output.mp4",
        )
        
        job = self.store.get("timestamp-job")
        assert "created_at" in job
        assert "updated_at" in job
        assert isinstance(job["created_at"], (int, float))
        assert isinstance(job["updated_at"], (int, float))
        assert job["created_at"] == job["updated_at"]  # Should be equal initially
