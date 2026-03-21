"""Unit tests for cloud_dispatch.py - Provider routing and error handling."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.providers.cloud_dispatch import render_cloud, _PROVIDERS


class TestCloudDispatch:
    """Test the cloud provider dispatch logic."""

    def test_unknown_provider_raises_value_error(self):
        """Test that an unknown provider name raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            render_cloud(
                provider="unknown_provider",
                prompt="test",
                storyboard={},
                image_paths=[Path("/fake/img.png")],
                out_path=Path("/fake/output.mp4"),
            )
        assert "unknown_provider" in str(exc_info.value)
        assert "Supported:" in str(exc_info.value)

    def test_unconfigured_provider_raises_runtime_error(self):
        """Test that an unconfigured provider raises RuntimeError with setup guidance."""
        # Patch is_configured to return False for kling
        with patch.object(_PROVIDERS["kling"], "is_configured", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                render_cloud(
                    provider="kling",
                    prompt="test",
                    storyboard={},
                    image_paths=[Path("/fake/img.png")],
                    out_path=Path("/fake/output.mp4"),
                )
        assert "kling" in str(exc_info.value)
        assert "not configured" in str(exc_info.value)

    def test_configured_provider_calls_render(self):
        """Test that a configured provider has render() called with correct context."""
        mock_provider = MagicMock()
        mock_provider.is_configured.return_value = True

        # Temporarily replace provider
        original = _PROVIDERS.get("kling")
        _PROVIDERS["kling"] = mock_provider
        try:
            render_cloud(
                provider="kling",
                prompt="A cute cat",
                storyboard={"fps": 30, "width": 720, "height": 1280},
                image_paths=[Path("/fake/cat.png")],
                out_path=Path("/fake/output.mp4"),
                bgm_path=Path("/fake/bgm.mp3"),
            )
            mock_provider.render.assert_called_once()
            ctx = mock_provider.render.call_args[0][0]
            assert ctx.provider == "kling"
            assert ctx.prompt == "A cute cat"
            assert ctx.out_path == Path("/fake/output.mp4")
            assert ctx.bgm_path == Path("/fake/bgm.mp3")
            assert len(ctx.image_paths) == 1
        finally:
            _PROVIDERS["kling"] = original

    def test_all_providers_registered(self):
        """Test that all expected providers are available in _PROVIDERS."""
        expected = {"kling", "openai", "gemini", "doubao"}
        assert expected.issubset(_PROVIDERS.keys())

    def test_render_cloud_no_bgm(self):
        """Test render_cloud works correctly when bgm_path is None."""
        mock_provider = MagicMock()
        mock_provider.is_configured.return_value = True

        original = _PROVIDERS.get("kling")
        _PROVIDERS["kling"] = mock_provider
        try:
            render_cloud(
                provider="kling",
                prompt="test",
                storyboard={},
                image_paths=[Path("/fake/img.png")],
                out_path=Path("/fake/out.mp4"),
                bgm_path=None,
            )
            ctx = mock_provider.render.call_args[0][0]
            assert ctx.bgm_path is None
        finally:
            _PROVIDERS["kling"] = original
