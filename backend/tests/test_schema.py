"""Unit tests for schema.py - Storyboard and Scene models."""
from __future__ import annotations

import pytest
from app.schema import Scene, Storyboard


class TestScene:
    """Test Scene model validation and methods."""

    def test_scene_valid_minimal(self):
        """Test minimal valid scene creation."""
        scene = Scene(duration_s=3.0, prompt="A cute cat")
        assert scene.duration_s == 3.0
        assert scene.prompt == "A cute cat"
        assert scene.subtitle is None

    def test_scene_with_subtitle(self):
        """Test scene with subtitle text."""
        scene = Scene(
            duration_s=5.0,
            prompt="Cat playing",
            subtitle="Hello!",
        )
        assert scene.subtitle == "Hello!"
        assert scene.duration_s == 5.0

    def test_scene_multiple_formats(self):
        """Test scene accepts different duration values."""
        scene = Scene(duration_s=1.5, prompt="Quick scene")
        assert scene.duration_s == 1.5

    def test_scene_default_prompt(self):
        """Test that default prompt is empty string."""
        scene = Scene(duration_s=3.0)
        assert scene.prompt == ""

    def test_scene_validation_min_duration(self):
        """Test that duration must be >= 0.5."""
        # Valid edge case
        scene = Scene(duration_s=0.5, prompt="minimum")
        assert scene.duration_s == 0.5

    def test_scene_validation_rejects_low_duration(self):
        """Test that duration below 0.5 is rejected."""
        with pytest.raises(Exception):  # pydantic ValidationError
            Scene(duration_s=0.1, prompt="too short")

    def test_scene_validation_rejects_negative_duration(self):
        """Test that negative duration is rejected."""
        with pytest.raises(Exception):
            Scene(duration_s=-1.0, prompt="negative")


class TestStoryboard:
    """Test Storyboard model validation and methods."""

    def test_storyboard_create_minimal(self):
        """Test creating a minimal storyboard."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        assert sb.width == 720
        assert sb.height == 1280
        assert sb.fps == 30
        assert sb.scenes == []

    def test_storyboard_with_scenes(self):
        """Test storyboard with scene list."""
        scenes = [
            Scene(duration_s=3.0, prompt="Opening"),
            Scene(duration_s=4.0, prompt="Middle"),
        ]
        sb = Storyboard(
            width=1280,
            height=720,
            fps=30,
            scenes=scenes,
        )
        assert len(sb.scenes) == 2
        assert sb.scenes[0].prompt == "Opening"
        assert sb.scenes[1].prompt == "Middle"

    def test_storyboard_autogen(self):
        """Test autogen method creates storyboard from prompt."""
        sb = Storyboard.autogen(prompt="Creating anime video", duration_s=12.0)
        assert sb is not None
        assert sb.duration_s == 12.0
        assert len(sb.scenes) == 3
        for scene in sb.scenes:
            assert scene.prompt == "Creating anime video"

    def test_storyboard_autogen_empty_prompt(self):
        """Test autogen with empty prompt uses default."""
        sb = Storyboard.autogen(prompt="", duration_s=9.0)
        assert len(sb.scenes) == 3
        # Each scene uses the prompt or default

    def test_storyboard_apply_template(self):
        """Test applying template to storyboard."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        custom_template = {
            "id": "tpl_001",
            "name": "Custom Template",
            "platform": "douyin",
            "width": 1080,
            "height": 1920,
            "duration_s": 30.0,
            "cover_width": 1080,
            "cover_height": 1920,
            "subtitle_safe_margin": 200,
        }
        result = sb.apply_template(custom_template)
        assert result is not None
        assert result.template_id == "tpl_001"
        assert result.template_name == "Custom Template"
        assert result.platform == "douyin"
        assert result.width == 1080
        assert result.height == 1920
        assert result.duration_s == 30.0
        assert result.subtitle_safe_margin == 200

    def test_storyboard_apply_template_partial(self):
        """Test applying partial template only updates provided fields."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        partial_template = {"platform": "tiktok", "width": 1080}
        result = sb.apply_template(partial_template)
        assert result.platform == "tiktok"
        assert result.width == 1080
        # Other fields unchanged
        assert result.height == 1280
        assert result.fps == 30

    def test_storyboard_apply_template_none(self):
        """Test applying None template returns original."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        result = sb.apply_template(None)
        assert result is sb  # Same instance

    def test_storyboard_platform_templates(self):
        """Test platform-specific templates."""
        platforms = ["douyin", "instagram_reels", "tiktok", "xiaohongshu"]
        for platform in platforms:
            sb = Storyboard(
                width=1080,
                height=1920,
                fps=30,
                scenes=[],
                platform=platform,
            )
            assert sb.platform == platform

    def test_storyboard_with_defaults(self):
        """Test with_defaults method recalculates duration from existing scenes."""
        sb = Storyboard(
            width=720,
            height=1280,
            fps=30,
            scenes=[
                Scene(duration_s=3.0, prompt="First scene"),
                Scene(duration_s=3.0, prompt=""),  # Empty prompt - not auto-filled
            ],
            duration_s=20.0,  # Initial duration set higher than scene sum
        )
        result = sb.with_defaults(prompt="Default prompt text")
        # with_defaults recalculates total duration from scenes
        assert result.duration_s == 6.0  # 3.0 + 3.0
        # Original scenes preserved as-is (empty prompts NOT auto-filled)
        assert result.scenes[0].prompt == "First scene"
        assert result.scenes[1].prompt == ""

    def test_storyboard_with_defaults_no_scenes(self):
        """Test with_defaults autogenerates scenes when list is empty."""
        sb = Storyboard(
            width=720,
            height=1280,
            fps=30,
            scenes=[],
            duration_s=15.0,
        )
        result = sb.with_defaults(prompt="Auto fill")
        # Should generate 3 scenes
        assert len(result.scenes) == 3
        # Each should have the default prompt
        for scene in result.scenes:
            assert scene.prompt == "Auto fill"

    def test_storyboard_custom_settings(self):
        """Test custom settings like subtitles and bgm_volume."""
        sb = Storyboard(
            width=1080,
            height=1920,
            fps=30,
            scenes=[],
            subtitles=True,
            bgm_volume=0.5,
        )
        assert sb.subtitles is True
        assert sb.bgm_volume == 0.5

    def test_storyboard_default_values(self):
        """Test that default values are set correctly."""
        sb = Storyboard()
        assert sb.fps == 30
        assert sb.width == 1280
        assert sb.height == 720
        assert sb.duration_s == 15.0
        assert sb.subtitles is True
        assert sb.bgm_volume == 0.25
        assert sb.x264_preset == "veryfast"
        assert sb.x264_crf == 26
        assert sb.x264_tune == "stillimage"
        assert sb.keep_tmp is False

    def test_storyboard_scenes_total_duration(self):
        """Test that storyboard duration equals sum of scene durations via with_defaults."""
        scenes = [
            Scene(duration_s=3.0, prompt="Scene 1"),
            Scene(duration_s=4.0, prompt="Scene 2"),
            Scene(duration_s=5.0, prompt="Scene 3"),
        ]
        sb = Storyboard(
            width=1280,
            height=720,
            fps=30,
            scenes=scenes,
            duration_s=12.0,
        )
        # with_defaults recalculates total duration
        result = sb.with_defaults(prompt="ignored")
        assert result.duration_s == 12.0  # User-set, not auto-calculated
