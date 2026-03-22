"""Unit tests for all T2I Providers."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from app.providers.t2i.base_t2i import (
    TextToImageProvider,
    T2IProviderField,
    T2IResult,
    T2ITaskSubmission,
)
from app.providers.t2i.jimeng_t2i import JimengT2IProvider
from app.providers.t2i.tongyi_t2i import TongyiWanxiangT2IProvider
from app.providers.t2i.dalle_t2i import DallET2IProvider
from app.providers.t2i.sd_t2i import StableDiffusionT2IProvider


@pytest.fixture
def valid_jimeng_config():
    return {"api_key": "sk-valid-api-key-12345678", "poll_interval_seconds": "3"}


@pytest.fixture
def valid_tongyi_config():
    return {"api_key": "sk-valid-api-key-12345678", "poll_interval_seconds": "3"}


@pytest.fixture
def valid_dalle_config():
    return {"api_key": "sk-valid-openai-key-12345678"}


@pytest.fixture
def valid_sd_config():
    return {"base_url": "http://localhost:7860"}


class TestProviderIdentity:
    @pytest.mark.parametrize("provider,expected_code,expected_name", [
        (JimengT2IProvider(), "jimeng", "即梦"),
        (TongyiWanxiangT2IProvider(), "tongyi", "通义万相"),
        (DallET2IProvider(), "dalle", "DALL-E"),
        (StableDiffusionT2IProvider(), "sd", "Stable Diffusion"),
    ])
    def test_code_returns_expected(self, provider, expected_code, expected_name):
        assert provider.code() == expected_code

    @pytest.mark.parametrize("provider,expected_code,expected_name", [
        (JimengT2IProvider(), "jimeng", "即梦"),
        (TongyiWanxiangT2IProvider(), "tongyi", "通义万相"),
        (DallET2IProvider(), "dalle", "DALL-E"),
        (StableDiffusionT2IProvider(), "sd", "Stable Diffusion"),
    ])
    def test_display_name_returns_expected(self, provider, expected_code, expected_name):
        assert provider.display_name() == expected_name

    @pytest.mark.parametrize("provider,expected_code", [
        (JimengT2IProvider(), "jimeng"),
        (TongyiWanxiangT2IProvider(), "tongyi"),
        (DallET2IProvider(), "dalle"),
        (StableDiffusionT2IProvider(), "sd"),
    ])
    def test_description_returns_non_empty(self, provider, expected_code):
        desc = provider.description()
        assert isinstance(desc, str)
        assert len(desc) > 0


class TestListConfigFields:
    def test_jimeng_returns_expected_field_count(self):
        provider = JimengT2IProvider()
        fields = provider.list_config_fields()
        assert len(fields) == 5
        keys = {f.key for f in fields}
        assert "api_key" in keys
        assert "base_url" in keys

    def test_tongyi_returns_expected_field_count(self):
        provider = TongyiWanxiangT2IProvider()
        fields = provider.list_config_fields()
        assert len(fields) == 7
        keys = {f.key for f in fields}
        assert "api_key" in keys
        assert "model" in keys
        assert "use_async" in keys

    def test_dalle_returns_expected_field_count(self):
        provider = DallET2IProvider()
        fields = provider.list_config_fields()
        assert len(fields) == 5
        keys = {f.key for f in fields}
        assert "api_key" in keys
        assert "model" in keys
        assert "quality" in keys

    def test_sd_returns_expected_field_count(self):
        provider = StableDiffusionT2IProvider()
        fields = provider.list_config_fields()
        assert len(fields) == 7
        keys = {f.key for f in fields}
        assert "base_url" in keys
        assert "steps" in keys
        assert "guidance_scale" in keys

    @pytest.mark.parametrize("provider", [
        JimengT2IProvider(),
        TongyiWanxiangT2IProvider(),
        DallET2IProvider(),
        StableDiffusionT2IProvider(),
    ])
    def test_fields_are_t2i_provider_field_instances(self, provider):
        fields = provider.list_config_fields()
        for f in fields:
            assert isinstance(f, T2IProviderField)
            assert isinstance(f.key, str)
            assert isinstance(f.label, str)
            assert isinstance(f.kind, str)

    @pytest.mark.parametrize("provider", [
        JimengT2IProvider(),
        TongyiWanxiangT2IProvider(),
        DallET2IProvider(),
    ])
    def test_required_api_key_field_present(self, provider):
        fields = provider.list_config_fields()
        api_key_field = next((f for f in fields if f.key == "api_key"), None)
        assert api_key_field is not None
        assert api_key_field.required is True


class TestValidateConfig:
    def test_jimeng_valid_config_returns_empty(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        errors = provider.validate_config(valid_jimeng_config)
        assert errors == []

    def test_jimeng_missing_api_key_returns_error(self):
        provider = JimengT2IProvider()
        errors = provider.validate_config({})
        assert len(errors) > 0
        assert any("API Key" in e or "api_key" in e.lower() for e in errors)

    def test_jimeng_short_api_key_returns_error(self):
        provider = JimengT2IProvider()
        errors = provider.validate_config({"api_key": "short"})
        assert len(errors) > 0

    def test_jimeng_invalid_poll_interval_returns_error(self):
        provider = JimengT2IProvider()
        errors = provider.validate_config(
            {"api_key": "sk-valid-api-key-12345678", "poll_interval_seconds": "-1"}
        )
        assert len(errors) > 0

    def test_tongyi_valid_config_returns_empty(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        errors = provider.validate_config(valid_tongyi_config)
        assert errors == []

    def test_tongyi_missing_api_key_returns_error(self):
        provider = TongyiWanxiangT2IProvider()
        errors = provider.validate_config({})
        assert len(errors) > 0

    def test_tongyi_invalid_base_url_returns_error(self):
        provider = TongyiWanxiangT2IProvider()
        errors = provider.validate_config(
            {"api_key": "sk-valid-api-key-12345678", "base_url": "not-a-url"}
        )
        assert len(errors) > 0

    def test_dalle_valid_config_returns_empty(self, valid_dalle_config):
        provider = DallET2IProvider()
        errors = provider.validate_config(valid_dalle_config)
        assert errors == []

    def test_dalle_missing_api_key_returns_error(self):
        provider = DallET2IProvider()
        errors = provider.validate_config({})
        assert len(errors) > 0

    def test_dalle_wrong_prefix_returns_error(self):
        provider = DallET2IProvider()
        errors = provider.validate_config({"api_key": "wrong-prefix-api-key"})
        assert len(errors) > 0

    def test_sd_valid_config_returns_empty(self, valid_sd_config):
        provider = StableDiffusionT2IProvider()
        errors = provider.validate_config(valid_sd_config)
        assert errors == []

    def test_sd_missing_base_url_returns_error(self):
        provider = StableDiffusionT2IProvider()
        errors = provider.validate_config({})
        assert len(errors) > 0

    def test_sd_invalid_steps_returns_error(self):
        provider = StableDiffusionT2IProvider()
        errors = provider.validate_config(
            {"base_url": "http://localhost:7860", "steps": 999}
        )
        assert len(errors) > 0

    def test_sd_invalid_guidance_scale_returns_error(self):
        provider = StableDiffusionT2IProvider()
        errors = provider.validate_config(
            {"base_url": "http://localhost:7860", "guidance_scale": 100.0}
        )
        assert len(errors) > 0


class TestGetCapabilities:
    @pytest.mark.parametrize("provider", [
        JimengT2IProvider(),
        TongyiWanxiangT2IProvider(),
        DallET2IProvider(),
        StableDiffusionT2IProvider(),
    ])
    def test_returns_dict_with_required_keys(self, provider):
        caps = provider.get_capabilities()
        assert isinstance(caps, dict)
        assert "supports_async" in caps
        assert "supports_sync" in caps
        assert "supports_styles" in caps
        assert "supports_negative_prompt" in caps
        assert "supports_image_size" in caps

    def test_jimeng_async_only(self):
        caps = JimengT2IProvider().get_capabilities()
        assert caps["supports_async"] is True
        assert caps["supports_sync"] is False

    def test_dalle_sync_only(self):
        caps = DallET2IProvider().get_capabilities()
        assert caps["supports_async"] is False
        assert caps["supports_sync"] is True

    def test_sd_sync_only(self):
        caps = StableDiffusionT2IProvider().get_capabilities()
        assert caps["supports_async"] is False
        assert caps["supports_sync"] is True

    def test_tongyi_supports_both_modes(self):
        caps = TongyiWanxiangT2IProvider().get_capabilities()
        assert caps["supports_async"] is True
        assert caps["supports_sync"] is True


class TestHealthcheck:
    def test_jimeng_invalid_config_returns_false(self):
        provider = JimengT2IProvider()
        ok, msg = provider.healthcheck({})
        assert ok is False
        assert msg is not None

    def test_jimeng_valid_config_returns_true(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        ok, msg = provider.healthcheck(valid_jimeng_config)
        assert ok is True
        assert msg is None

    def test_tongyi_invalid_config_returns_false(self):
        provider = TongyiWanxiangT2IProvider()
        ok, msg = provider.healthcheck({})
        assert ok is False

    def test_tongyi_valid_config_returns_true(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        ok, msg = provider.healthcheck(valid_tongyi_config)
        assert ok is True

    def test_dalle_invalid_config_returns_false(self):
        provider = DallET2IProvider()
        ok, msg = provider.healthcheck({})
        assert ok is False

    def test_dalle_valid_config_returns_true(self, valid_dalle_config):
        provider = DallET2IProvider()
        ok, msg = provider.healthcheck(valid_dalle_config)
        assert ok is True

    def test_sd_invalid_config_returns_false(self):
        provider = StableDiffusionT2IProvider()
        ok, msg = provider.healthcheck({})
        assert ok is False

    def test_sd_valid_config_returns_true(self, valid_sd_config):
        provider = StableDiffusionT2IProvider()
        ok, msg = provider.healthcheck(valid_sd_config)
        assert ok is True


class TestGenerateInvalidConfig:
    def test_jimeng_missing_api_key_raises(self):
        provider = JimengT2IProvider()
        with pytest.raises(ValueError):
            provider.generate(prompt="a cat", config={})

    def test_tongyi_missing_api_key_raises(self):
        provider = TongyiWanxiangT2IProvider()
        with pytest.raises(ValueError):
            provider.generate(prompt="a cat", config={})

    def test_dalle_missing_api_key_raises(self):
        provider = DallET2IProvider()
        with pytest.raises(ValueError):
            provider.generate(prompt="a cat", config={})

    def test_sd_missing_base_url_raises(self):
        provider = StableDiffusionT2IProvider()
        with pytest.raises(ValueError):
            provider.generate(prompt="a cat", config={})

    def test_jimeng_valid_config_no_validation_error(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        import urllib.error
        try:
            result = provider.generate(prompt="a cat", config=valid_jimeng_config)
            assert isinstance(result, T2IResult)
        except urllib.error.URLError:
            pass  # Expected without real API

    def test_tongyi_valid_config_no_validation_error(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        import urllib.error
        try:
            result = provider.generate(prompt="a cat", config=valid_tongyi_config)
            assert isinstance(result, T2IResult)
        except urllib.error.URLError:
            pass

    def test_dalle_valid_config_no_validation_error(self, valid_dalle_config):
        provider = DallET2IProvider()
        import urllib.error
        try:
            result = provider.generate(prompt="a cat", config=valid_dalle_config)
            assert isinstance(result, T2IResult)
        except urllib.error.URLError:
            pass

    def test_sd_valid_config_no_validation_error(self, valid_sd_config):
        provider = StableDiffusionT2IProvider()
        import urllib.error
        try:
            result = provider.generate(prompt="a cat", config=valid_sd_config)
            assert isinstance(result, T2IResult)
        except urllib.error.URLError:
            pass


class TestSubmitReturnsTaskSubmission:
    def _mock_response(self, response_data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_jimeng_submit_returns_task_submission(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response(
                {"request_id": "task-123", "status": "pending"}
            )
            submission = provider.submit(prompt="a cat", config=valid_jimeng_config)
            assert isinstance(submission, T2ITaskSubmission)
            assert submission.provider_task_id == "task-123"
            assert submission.normalized_status == "submitted"
            assert submission.request_payload["prompt"] == "a cat"

    def test_tongyi_submit_sync_returns_task_submission(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "output": {"image_url": "https://example.com/cat.png"}
            })
            submission = provider.submit(prompt="a cat", config=valid_tongyi_config)
            assert isinstance(submission, T2ITaskSubmission)
            assert submission.provider_task_id.startswith("sync-tongyi-")
            assert submission.normalized_status == "done"

    def test_dalle_submit_returns_task_submission(self, valid_dalle_config):
        provider = DallET2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "data": [{"url": "https://example.com/image.png", "revised_prompt": "a cat"}]
            })
            submission = provider.submit(prompt="a cat", config=valid_dalle_config)
            assert isinstance(submission, T2ITaskSubmission)
            assert submission.normalized_status == "done"

    def test_sd_submit_returns_task_submission(self, valid_sd_config):
        provider = StableDiffusionT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "images": ["aGVsbG9fd29ybGQ="],
                "parameters": {},
                "info": "",
            })
            submission = provider.submit(prompt="a cat", config=valid_sd_config)
            assert isinstance(submission, T2ITaskSubmission)
            assert submission.normalized_status == "done"

    def test_jimeng_submit_http_error_returns_failed_submission(self, valid_jimeng_config):
        import urllib.error
        provider = JimengT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="http://test", code=401, msg="Unauthorized", hdrs={}, fp=None
            )
            submission = provider.submit(prompt="a cat", config=valid_jimeng_config)
            assert isinstance(submission, T2ITaskSubmission)
            assert submission.normalized_status == "failed"


class TestPollReturnsT2IResult:
    def _mock_response(self, response_data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_jimeng_poll_success_returns_done(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "request_id": "task-123",
                "status": "success",
                "image_url": "https://example.com/image.png",
            })
            result = provider.poll(provider_task_id="task-123", config=valid_jimeng_config)
            assert isinstance(result, T2IResult)
            assert result.normalized_status == "done"
            assert result.image_url == "https://example.com/image.png"

    def test_jimeng_poll_failed_returns_failed(self, valid_jimeng_config):
        provider = JimengT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "request_id": "task-123",
                "status": "failed",
                "error": "content violation",
            })
            result = provider.poll(provider_task_id="task-123", config=valid_jimeng_config)
            assert isinstance(result, T2IResult)
            assert result.normalized_status == "failed"

    def test_tongyi_poll_success_returns_done(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = self._mock_response({
                "request_id": "task-123",
                "status": "SUCCEEDED",
                "output": {"image_url": "https://example.com/cat.png"},
            })
            result = provider.poll(provider_task_id="task-123", config=valid_tongyi_config)
            assert isinstance(result, T2IResult)
            assert result.normalized_status == "done"
            assert result.image_url == "https://example.com/cat.png"

    def test_tongyi_poll_empty_task_id_returns_failed(self, valid_tongyi_config):
        provider = TongyiWanxiangT2IProvider()
        result = provider.poll(provider_task_id="", config=valid_tongyi_config)
        assert isinstance(result, T2IResult)
        assert result.normalized_status == "failed"

    def test_sd_poll_default_returns_failed(self, valid_sd_config):
        """SD is sync-only, poll() should return failed by default."""
        provider = StableDiffusionT2IProvider()
        result = provider.poll(provider_task_id="any-task-id", config=valid_sd_config)
        assert isinstance(result, T2IResult)
        assert result.normalized_status == "failed"

    def test_dalle_poll_default_returns_failed(self, valid_dalle_config):
        """DALL-E is sync-only, poll() should return failed by default."""
        provider = DallET2IProvider()
        result = provider.poll(provider_task_id="any-task-id", config=valid_dalle_config)
        assert isinstance(result, T2IResult)
        assert result.normalized_status == "failed"


class TestNormalizeResult:
    """Test normalize_result() sets normalized_status correctly."""

    def test_result_with_image_url_sets_done(self):
        provider = JimengT2IProvider()
        result = T2IResult(image_url="https://example.com/image.png", normalized_status="pending")
        normalized = provider.normalize_result(result)
        assert normalized.normalized_status == "done"
        assert normalized.image_url == "https://example.com/image.png"

    def test_result_with_image_b64_sets_done(self):
        provider = JimengT2IProvider()
        result = T2IResult(image_b64="abc123xyz", normalized_status="pending")
        normalized = provider.normalize_result(result)
        assert normalized.normalized_status == "done"
        assert normalized.image_b64 == "abc123xyz"

    def test_result_without_image_sets_failed(self):
        provider = JimengT2IProvider()
        result = T2IResult(normalized_status="pending", raw_response={})
        normalized = provider.normalize_result(result)
        assert normalized.normalized_status == "failed"


class TestT2IDataClasses:
    """Test T2IResult and T2ITaskSubmission dataclasses."""

    def test_t2i_result_to_dict(self):
        result = T2IResult(
            image_url="https://example.com/image.png",
            normalized_prompt="a cat",
            normalized_status="done",
            raw_response={"status": "success"},
        )
        d = result.to_dict()
        assert d["image_url"] == "https://example.com/image.png"
        assert d["normalized_prompt"] == "a cat"
        assert d["normalized_status"] == "done"
        assert d["raw_response"]["status"] == "success"

    def test_t2i_task_submission_fields(self):
        submission = T2ITaskSubmission(
            provider_task_id="task-123",
            provider_status="pending",
            normalized_status="submitted",
            request_payload={"prompt": "a cat"},
            raw_response={"request_id": "task-123"},
        )
        assert submission.provider_task_id == "task-123"
        assert submission.normalized_status == "submitted"
        assert submission.request_payload["prompt"] == "a cat"

    def test_t2i_provider_field_to_dict(self):
        field = T2IProviderField(
            key="api_key",
            label="API Key",
            kind="password",
            required=True,
            placeholder="sk-xxx",
            help_text="API key for the provider",
            options=[{"label": "opt1", "value": "val1"}],
        )
        d = field.to_dict()
        assert d["key"] == "api_key"
        assert d["label"] == "API Key"
        assert d["kind"] == "password"
        assert d["required"] is True
        assert d["options"][0]["value"] == "val1"
