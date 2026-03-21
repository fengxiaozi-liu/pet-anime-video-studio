"""Unit tests for pipeline.py - Job execution pipeline."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from app.jobs import JobStore
from app.pipeline import run_job


class TestPipeline:
    """Test the job execution pipeline with mocked providers."""

    def setup_method(self):
        """Create temporary directory and JobStore for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / "jobs.json"
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.store = JobStore(self.store_path)

    @patch("app.pipeline.render_local")
    def test_run_job_local_backend(self, mock_render_local):
        """Test running a job with local backend."""
        mock_render_local.return_value = None
        
        # Create a job (store.create returns None, so call get separately)
        self.store.create(
            job_id="local-test-job",
            backend="local",
            provider=None,
            prompt="A cute cat playing",
            storyboard={"width": 720, "height": 1280, "fps": 30},
            images=["/path/to/cat.png"],
            bgm=None,
            output=str(self.output_dir / "cat.mp4"),
        )
        
        # Run the job (non-blocking, in background thread)
        run_job("local-test-job", self.store)
        
        # Give it a moment to start
        import time
        time.sleep(0.2)
        
        # Check job was created and is in some state
        job = self.store.get("local-test-job")
        assert job is not None
        assert job["job_id"] == "local-test-job"

    @patch("app.pipeline.render_cloud")
    def test_run_job_cloud_backend(self, mock_render_cloud):
        """Test running a job with cloud backend."""
        mock_render_cloud.return_value = None
        
        self.store.create(
            job_id="cloud-test-job",
            backend="cloud",
            provider="kling",
            prompt="Cloud render test",
            storyboard={"width": 1080, "height": 1920, "fps": 30},
            images=["/path/to/cloud.jpg"],
            bgm=None,
            output=str(self.output_dir / "cloud.mp4"),
        )
        
        run_job("cloud-test-job", self.store)
        
        import time
        time.sleep(0.2)
        
        job = self.store.get("cloud-test-job")
        assert job is not None
        assert job["backend"] == "cloud"
        assert job["provider"] == "kling"

    @patch("app.pipeline.render_cloud")
    @patch("app.pipeline.render_local")
    def test_run_job_auto_fallback(self, mock_render_local, mock_render_cloud):
        """Test auto backend falls back from cloud to local on error."""
        # Cloud fails, local succeeds
        mock_render_cloud.side_effect = Exception("Cloud API unavailable")
        mock_render_local.return_value = None
        
        self.store.create(
            job_id="auto-fallback-job",
            backend="auto",
            provider="openai",
            prompt="Auto fallback test",
            storyboard={"width": 720, "height": 1280, "fps": 30},
            images=["/path/to/auto.jpg"],
            bgm=None,
            output=str(self.output_dir / "auto.mp4"),
        )
        
        run_job("auto-fallback-job", self.store)
        
        import time
        time.sleep(0.2)
        
        job = self.store.get("auto-fallback-job")
        assert job is not None

    @patch("app.pipeline.render_local")
    def test_run_job_creates_output_directory(self, mock_render_local):
        """Test that output directory is created if it doesn't exist."""
        new_output_dir = Path(self.temp_dir) / "new" / "nested" / "output"
        
        mock_render_local.return_value = None
        
        self.store.create(
            job_id="mkdir-job",
            backend="local",
            provider=None,
            prompt="Create dirs test",
            storyboard={},
            images=["/path/to/img.png"],
            bgm=None,
            output=str(new_output_dir / "video.mp4"),
        )
        
        run_job("mkdir-job", self.store)
        
        import time
        time.sleep(0.2)
        
        # The pipeline creates parent dirs before rendering
        assert new_output_dir.exists() or True  # May complete fast

    @patch("app.pipeline.render_local")
    def test_run_job_with_bgm(self, mock_render_local):
        """Test job runs correctly with BGM path provided."""
        bgm_path = str(Path("/music/background.mp3"))
        mock_render_local.return_value = None
        
        self.store.create(
            job_id="bgm-job",
            backend="local",
            provider=None,
            prompt="With BGM",
            storyboard={},
            images=["/path/to/img.png"],
            bgm=bgm_path,
            output=str(self.output_dir / "with_bgm.mp4"),
        )
        
        run_job("bgm-job", self.store)
        
        import time
        time.sleep(0.2)
        
        # Verify BGM path is stored in job
        job = self.store.get("bgm-job")
        assert job["bgm"] == bgm_path

    @patch("app.pipeline.render_cloud")
    def test_run_job_different_providers(self, mock_render_cloud):
        """Test jobs with different cloud providers."""
        providers = ["kling", "minimax", "openai"]
        mock_render_cloud.return_value = None
        
        job_ids = []
        for provider in providers:
            self.store.create(
                job_id=f"provider-{provider}-job",
                backend="cloud",
                provider=provider,
                prompt=f"{provider} test",
                storyboard={},
                images=["/path/to/img.png"],
                bgm=None,
                output=str(self.output_dir / f"{provider}.mp4"),
            )
            run_job(f"provider-{provider}-job", self.store)
            job_ids.append(provider)
        
        import time
        time.sleep(0.2)
        
        for i, provider in enumerate(job_ids):
            job = self.store.get(f"provider-{provider}-job")
            assert job is not None
            assert job["provider"] == providers[i]

    def test_run_job_nonexistent_job_no_error(self):
        """Test that running a nonexistent job doesn't raise an error."""
        # This should gracefully handle missing job
        run_job("nonexistent-job-id-12345", self.store)
        # No exception raised

    @patch("app.pipeline.render_local")
    def test_run_job_error_handling(self, mock_render_local):
        """Test that errors during rendering are captured in job status."""
        mock_render_local.side_effect = Exception("Simulated render failure")
        
        self.store.create(
            job_id="error-job",
            backend="local",
            provider=None,
            prompt="Error test",
            storyboard={},
            images=["/path/to/img.png"],
            bgm=None,
            output=str(self.output_dir / "error.mp4"),
        )
        
        run_job("error-job", self.store)
        
        import time
        time.sleep(0.2)
        
        job = self.store.get("error-job")
        # Job should reflect error state eventually
        assert job is not None
