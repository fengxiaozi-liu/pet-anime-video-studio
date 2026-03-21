"""Unit tests for assets.py - AssetStore functionality."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from app.assets import AssetStore


class TestAssetStore:
    """Test AssetStore CRUD operations and thread safety."""

    def setup_method(self):
        """Create temporary directories and AssetStore for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir = Path(self.temp_dir) / "assets"
        self.index_path = Path(self.temp_dir) / "assets.json"
        self.store = AssetStore(root_dir=self.root_dir, index_path=self.index_path)

    def test_add_asset_success(self):
        """Test adding a new asset succeeds."""
        test_data = b"test image data"
        
        result = self.store.add(
            kind="image",
            filename="test.png",
            suffix=".png",
            bytes_data=test_data,
        )
        
        assert result["asset_id"] is not None
        assert result["kind"] == "image"
        assert result["filename"] == "test.png"
        assert result["size"] == len(test_data)
        assert "path" in result
        assert "created_at" in result
        
        # Verify file was created
        asset_file = Path(result["path"])
        assert asset_file.exists()
        assert asset_file.read_bytes() == test_data

    def test_get_existing_asset(self):
        """Test retrieving an existing asset."""
        test_data = b"test data"
        meta = self.store.add(
            kind="video",
            filename="video.mp4",
            suffix=".mp4",
            bytes_data=test_data,
        )
        
        retrieved = self.store.get(meta["asset_id"])
        assert retrieved is not None
        assert retrieved["asset_id"] == meta["asset_id"]
        assert retrieved["kind"] == "video"
        assert retrieved["filename"] == "video.mp4"

    def test_get_nonexistent_asset_returns_none(self):
        """Test getting a nonexistent asset returns None."""
        result = self.store.get("nonexistent-asset-id")
        assert result is None

    def test_list_recent_assets(self):
        """Test listing recent assets returns them sorted by creation time (newest first)."""
        import time
        # Add multiple assets with small delay to ensure distinct timestamps
        for i in range(3):
            self.store.add(
                kind="image",
                filename=f"image_{i}.png",
                suffix=".png",
                bytes_data=f"data{i}".encode(),
            )
            time.sleep(0.01)  # Float timestamps provide sub-second precision
        
        # List with limit of 2
        recent = self.store.list_recent(limit=2)
        assert len(recent) == 2
        # Most recent first (image_2 added last)
        assert "image_2.png" in recent[0]["filename"]
        assert "image_1.png" in recent[1]["filename"]

    def test_list_respects_limit(self):
        """Test that list_recent respects the limit parameter."""
        # Add 5 assets
        for i in range(5):
            self.store.add(
                kind="audio",
                filename=f"audio_{i}.mp3",
                suffix=".mp3",
                bytes_data=f"audio_data_{i}".encode(),
            )
        
        recent = self.store.list_recent(limit=3)
        assert len(recent) == 3

    def test_root_dir_created_if_not_exists(self):
        """Test that root directory is created automatically."""
        temp_dir = tempfile.mkdtemp()
        custom_root = Path(temp_dir) / "nested" / "path" / "assets"
        index_path = Path(temp_dir) / "index.json"
        
        store = AssetStore(root_dir=custom_root, index_path=index_path)
        
        # Root dir should not exist yet
        assert not custom_root.exists()
        
        # Adding asset should create it
        store.add(
            kind="image",
            filename="test.png",
            suffix=".png",
            bytes_data=b"test",
        )
        
        assert custom_root.exists()

    def test_index_file_persistence(self):
        """Test that index file persists metadata correctly."""
        meta = self.store.add(
            kind="image",
            filename="persistent.png",
            suffix=".png",
            bytes_data=b"persistent_data",
        )
        
        # Index file should exist
        assert self.index_path.exists()
        
        # Verify JSON content
        import json
        data = json.loads(self.index_path.read_text("utf-8"))
        assert meta["asset_id"] in data
        assert data[meta["asset_id"]]["filename"] == "persistent.png"

    def test_multiple_kinds(self):
        """Test adding different kinds of assets."""
        kinds = [
            ("image", "photo.jpg", b"jpg_data"),
            ("audio", "music.mp3", b"mp3_data"),
            ("video", "clip.mp4", b"mp4_data"),
        ]
        
        results = []
        for kind, filename, data in kinds:
            suffix = Path(filename).suffix
            result = self.store.add(kind=kind, filename=filename, suffix=suffix, bytes_data=data)
            results.append(result)
        
        assert all(r["asset_id"] is not None for r in results)
        assert results[0]["kind"] == "image"
        assert results[1]["kind"] == "audio"
        assert results[2]["kind"] == "video"

    def test_atomic_write_with_tmp_file(self):
        """Test that index updates use atomic tmp file replacement."""
        # Add first asset
        self.store.add(
            kind="image",
            filename="first.png",
            suffix=".png",
            bytes_data=b"first",
        )
        
        # Verify no .tmp file exists after write
        tmp_path = self.index_path.with_suffix(self.index_path.suffix + ".tmp")
        assert not tmp_path.exists()
        
        # Add second asset
        self.store.add(
            kind="image",
            filename="second.png",
            suffix=".png",
            bytes_data=b"second",
        )
        
        # Still no .tmp file
        assert not tmp_path.exists()
        
        # Both assets should be in index
        data = self.store._load()
        assert len(data) == 2
