from app.character_image_assistants import (
    _extract_candidate_url,
    _raise_payload_error,
    _openai_image_url,
    _openai_task_url,
)


def test_openai_image_url_uses_configured_full_url():
    assert _openai_image_url("https://api.openai.com/v1") == "https://api.openai.com/v1"


def test_openai_image_url_keeps_full_generation_endpoint():
    assert (
        _openai_image_url("https://api.minimax.io/v1/image_generation")
        == "https://api.minimax.io/v1/image_generation"
    )


def test_openai_task_url_uses_api_root_from_full_generation_endpoint():
    assert (
        _openai_task_url("https://api-inference.modelscope.cn/v1/images/generations", "task-1")
        == "https://api-inference.modelscope.cn/v1/tasks/task-1"
    )


def test_openai_task_url_uses_api_root_from_base_url():
    assert (
        _openai_task_url("https://api-inference.modelscope.cn/", "task-1")
        == "https://api-inference.modelscope.cn/v1/tasks/task-1"
    )


def test_extract_candidate_url_reads_minimax_image_urls():
    assert _extract_candidate_url({"data": {"image_urls": ["https://example.com/image.png"]}}) == "https://example.com/image.png"


def test_raise_payload_error_reads_minimax_base_resp():
    try:
        _raise_payload_error({"base_resp": {"status_code": 1008, "status_msg": "invalid model"}})
    except ValueError as exc:
        assert "invalid model" in str(exc)
    else:
        raise AssertionError("Expected MiniMax base_resp error")
