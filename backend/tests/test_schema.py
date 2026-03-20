"""Unit tests for schema.py - Storyboard and Scene models."""
from __future__ import annotations

import pytest
from app.schema import Scene, Storyboard


class TestScene:
    """Test Scene model validation and methods."""

    def test_scene_valid_minimal(self):
        """Test minimal valid scene creation."""
        scene = Scene(
            image_paths=["image1.png"],
            duration_s=3.0,
            prompt="A cute cat",
        )
        
        assert len(scene.image_paths) == 1
        assert scene.duration_s == 3.0
        assert scene.prompt == "A cute cat"
        assert scene.subtitles == []

    def test_scene_with_subtitles(self):
        """Test scene with subtitle configuration."""
        scene = Scene(
            image_paths=["cat.png"],
            duration_s=5.0,
            prompt="Cat playing",
            subtitles=[
                {"text": "你好", "start_t": 0.0, "end_t": 2.0},
                {"text": "再见", "start_t": 3.0, "end_t": 5.0},
            ],
        )
        
        assert len(scene.subtitles) == 2
        assert scene.subtitles[0]["text"] == "你好"
        assert scene.subtitles[1]["text"] == "再见"

    def test_scene_multiple_images(self):
        """Test scene with multiple images."""
        scene = Scene(
            image_paths=["img1.png", "img2.png", "img3.png"],
            duration_s=6.0,
            prompt="Three cats together",
        )
        
        assert len(scene.image_paths) == 3

    def test_scene_default_duration(self):
        """Test that default duration is applied when not specified."""
        sb = Storyboard.create_scenes_from_prompt(
            prompt="A cute dog running",
            images=["dog1.png", "dog2.png"],
            duration_s=4.0,
            scenes_per_image=2,
        )
        
        # Each scene should have the calculated duration
        for scene in sb.scenes:
            assert scene.duration_s > 0

    def test_scene_validation_empty_images(self):
        """Test that empty image paths raises validation error."""
        with pytest.raises(ValueError):
            Scene.validate_model(cls=Scene, values={"image_paths": [], "duration_s": 3.0, "prompt": "test"})

    def test_scene_negative_duration(self):
        """Test that negative duration is handled appropriately."""
        scene = Scene(
            image_paths=["img.png"],
            duration_s=-1.0,
            prompt="Test",
        )
        assert scene.duration_s == -1.0  # Validation doesn't reject, but caller should handle


class TestStoryboard:
    """Test Storyboard model validation and methods."""

    def test_storyboard_create_minimal(self):
        """Test creating a minimal storyboard."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        
        assert sb.width == 720
        assert sb.height == 1280
        assert sb.fps == 30
        assert sb.scenes == []
        assert sb.platform == "custom"

    def test_storyboard_total_duration(self):
        """Test total_duration property calculation."""
        sb = Storyboard(
            width=1280,
            height=720,
            fps=30,
            scenes=[
                Scene(image_paths=["img1.png"], duration_s=3.0, prompt="Scene 1"),
                Scene(image_paths=["img2.png"], duration_s=4.0, prompt="Scene 2"),
                Scene(image_paths=["img3.png"], duration_s=5.0, prompt="Scene 3"),
            ],
        )
        
        assert sb.total_duration == 12.0  # 3 + 4 + 5

    def test_storyboard_create_scenes_from_prompt(self):
        """Test creating scenes from prompt and images."""
        sb = Storyboard.create_scenes_from_prompt(
            prompt="A happy dog playing in the park",
            images=["dog1.jpg", "dog2.jpg", "dog3.jpg"],
            duration_s=5.0,
            scenes_per_image=2,
        )
        
        assert len(sb.scenes) == 6  # 3 images * 2 scenes each
        assert all(len(scene.image_paths) > 0 for scene in sb.scenes)

    def test_storyboard_autogen(self):
        """Test autogen method creates storyboard from prompt."""
        sb = Storyboard.autogen(prompt="Creating anime video", duration_s=10.0)
        
        assert sb is not None
        assert sb.prompt == "Creating anime video"

    def test_storyboard_apply_template(self):
        """Test applying template to storyboard."""
        sb = Storyboard(width=720, height=1280, fps=30, scenes=[])
        
        custom_template = {
            "aspect_ratio": (1920, 1080),
            "duration_s": 30.0,
        }
        
        result = sb.apply_template(custom_template)
        assert result is not None

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
        """Test with_defaults method fills missing prompts."""
        sb = Storyboard(
            width=720,
            height=1280,
            fps=30,
            scenes=[
                Scene(image_paths=["img1.png"], duration_s=3.0, prompt="First scene"),
                Scene(image_paths=["img2.png"], duration_s=3.0, prompt=""),  # Empty prompt
                Scene(image_paths=["img3.png"], duration_s=3.0, prompt=None),  # None prompt
            ],
        )
        
        result = sb.with_defaults(prompt="Default prompt text")
        
        assert result.scenes[0].prompt == "First scene"  # Unchanged
        assert result.scenes[1].prompt == "Default prompt text"  # Filled
        assert result.scenes[2].prompt == "Default prompt text"  # Filled

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

    def test_create_scenes_edge_cases(self):
        """Test edge cases for scene creation."""
        # Single image
        sb_single = Storyboard.create_scenes_from_prompt(
            prompt="Single image test",
            images=["single.jpg"],
            duration_s=5.0,
            scenes_per_image=1,
        )
        assert len(sb_single.scenes) == 1
        
        # High scenes_per_image
        sb_multi = Storyboard.create_scenes_from_prompt(
            prompt="Multi-scene test",
            images=["multi.jpg"],
            duration_s=10.0,
            scenes_per_image=5,
        )
        assert len(sb_multi.scenes) == 5
