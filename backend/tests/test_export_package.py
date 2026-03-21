"""
Tests for export_package.py (M3 export package).
"""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.export_package import (
    _generate_caption,
    _generate_title,
    _get_hashtags,
    _build_project_json,
    generate_export_package,
)


class TestCaptionGeneration:
    def test_generate_caption_from_prompt(self):
        caption = _generate_caption("我家猫咪今天超可爱", "douyin")
        assert "我家猫咪今天超可爱" in caption
        assert len(caption) <= 150

    def test_generate_caption_truncates_long_prompt(self):
        long_prompt = " ".join(["word"] * 100)
        caption = _generate_caption(long_prompt, "douyin")
        assert len(caption) <= 150

    def test_generate_caption_empty_prompt(self):
        caption = _generate_caption("", "xiaohongshu")
        assert len(caption) <= 150

    def test_different_platform_emoji(self):
        dy = _generate_caption("test", "douyin")
        xhs = _generate_caption("test", "xiaohongshu")
        assert dy != xhs  # different emoji suffix


class TestTitleGeneration:
    def test_title_from_template_name(self):
        title = _generate_title("prompt", "douyin", "抖音 25s 竖屏")
        assert title == "抖音 25s 竖屏"

    def test_title_from_prompt(self):
        title = _generate_title("超可爱的橘猫每天早上叫我起床", "douyin", None)
        assert "超可爱的橘猫每天早上叫我起床" in title
        assert len(title) <= 200

    def test_title_fallback_platform_label(self):
        title = _generate_title("", "douyin", None)
        assert "抖音" in title

    def test_title_unknown_platform(self):
        title = _generate_title("", "unknown", None)
        assert len(title) > 0


class TestHashtagGeneration:
    def test_returns_correct_count(self):
        tags = _get_hashtags("douyin", count=5)
        assert len(tags) == 5

    def test_douyin_has_required_tag(self):
        tags = _get_hashtags("douyin")
        assert "#宠物" in tags

    def test_xiaohongshu_has_required_tag(self):
        tags = _get_hashtags("xiaohongshu")
        assert "#宠物" in tags

    def test_unknown_platform_falls_back_to_douyin(self):
        tags = _get_hashtags("unknown")
        assert "#宠物" in tags


class TestProjectJson:
    def test_build_project_json_basic(self):
        job = {
            "job_id": "test-123",
            "created_at": "2026-03-21T10:00:00+08:00",
            "prompt": "my cute cat",
            "platform": "douyin",
            "backend": "auto",
            "provider": "kling",
            "template_id": "douyin-25",
            "template_name": "抖音 25s 竖屏",
            "storyboard": {"duration_s": 25},
            "images": ["/path/to/img.png"],
            "bgm": "/path/to/bgm.mp3",
        }
        result = _build_project_json(job)
        assert result["version"] == "1.0"
        assert result["job_id"] == "test-123"
        assert result["prompt"] == "my cute cat"
        assert result["platform"] == "douyin"
        assert result["template"]["id"] == "douyin-25"
        assert result["storyboard"]["duration_s"] == 25

    def test_project_json_minimal_job(self):
        job = {"job_id": "min-1", "created_at": "2026-01-01T00:00:00Z"}
        result = _build_project_json(job)
        assert result["job_id"] == "min-1"
        assert result["template"] == {}


class TestExportPackageIntegration:
    """Integration tests using a real (small) zip file."""

    def test_generate_export_package_missing_job(self):
        mock_store = MagicMock()
        mock_store.get.return_value = None
        result = generate_export_package("no-such-id", mock_store, Path("/tmp"))
        assert result is None

    def test_generate_export_package_incomplete_job(self):
        mock_store = MagicMock()
        mock_store.get.return_value = {"job_id": "abc", "status": "running"}
        result = generate_export_package("abc", mock_store, Path("/tmp"))
        assert result is None

    @patch("app.export_package._extract_cover")
    def test_generate_export_package_complete_job(self, mock_extract, tmp_path):
        # Create a fake "video" file
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake video content")

        job = {
            "job_id": "export-test",
            "created_at": "2026-03-21T10:00:00+08:00",
            "status": "done",
            "output": str(video),
            "prompt": " cute cat video",
            "platform": "douyin",
            "backend": "local",
            "provider": None,
            "template_id": "douyin-25",
            "template_name": "抖音 25s 竖屏",
            "storyboard": {"duration_s": 25},
            "images": [],
            "bgm": None,
        }
        mock_store = MagicMock()
        mock_store.get.return_value = job

        # Simulate cover extraction returning a fake cover
        fake_cover = tmp_path / "test.cover.png"
        fake_cover.write_bytes(b"fake png")
        mock_extract.return_value = fake_cover

        zip_path = generate_export_package("export-test", mock_store, tmp_path)
        assert zip_path is not None
        assert zip_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "video.mp4" in names
            assert "cover.png" in names
            assert "title.txt" in names
            assert "caption.txt" in names
            assert "hashtags.txt" in names
            assert "project.json" in names

            # Verify project.json is valid
            pj = json.loads(zf.read("project.json").decode("utf-8"))
            assert pj["job_id"] == "export-test"
            assert pj["template"]["id"] == "douyin-25"

            # Verify title/caption/hashtags are non-empty
            assert len(zf.read("title.txt").decode("utf-8")) > 0
            assert len(zf.read("hashtags.txt").decode("utf-8")) > 0
