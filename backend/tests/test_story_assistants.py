import json

from app.story_assistants import (
    STORY_DRAFT_TOOL_NAME,
    _anthropic_story_tool,
    _build_user_prompt,
    _extract_anthropic_tool_payload,
    _extract_json_payload,
    _normalize_story_response,
    _openai_story_response_format,
)


def test_extract_json_payload_accepts_direct_object():
    payload = _extract_json_payload('{"story_summary":"概览","scenes":[]}')

    assert payload["story_summary"] == "概览"


def test_extract_json_payload_accepts_fenced_object():
    payload = _extract_json_payload('```json\n{"story_summary":"概览","scenes":[]}\n```')

    assert payload["story_summary"] == "概览"


def test_extract_json_payload_accepts_json_string_wrapped_object():
    wrapped = json.dumps('{"story_summary":"概览","scenes":[]}', ensure_ascii=False)

    payload = _extract_json_payload(wrapped)

    assert payload["story_summary"] == "概览"


def test_build_user_prompt_requires_plain_json_object():
    prompt = _build_user_prompt(
        prompt="城市宣传片",
        aspect_ratio="9:16",
        template_name="短视频",
        visual_style_name="写实",
        visual_style_prompt="自然光",
        characters=[],
    )

    assert "只返回一个 JSON 对象" in prompt
    assert "首字符必须是 {" in prompt


def test_normalize_story_response_accepts_common_alias_fields():
    payload = {
        "story_overview": "一只小狗与主人相伴成长。",
        "story_planning": "整体基调温暖治愈。",
        "storyboard": [
            {
                "scene_title": "初遇",
                "description": "春日公园里，主人第一次遇见小狗。",
                "caption": "从这一天开始，我们成为彼此的家人。",
                "duration": 5,
            }
        ],
    }

    result = _normalize_story_response(payload, [])

    assert result["story_summary"] == "一只小狗与主人相伴成长。"
    assert result["story_text"] == "整体基调温暖治愈。"
    assert result["scenes"][0]["title"] == "初遇"
    assert result["scenes"][0]["prompt"] == "春日公园里，主人第一次遇见小狗。"
    assert result["scenes"][0]["subtitle"] == "从这一天开始，我们成为彼此的家人。"
    assert result["scenes"][0]["duration_s"] == 5


def test_openai_response_format_uses_strict_json_schema():
    response_format = _openai_story_response_format()

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["story_summary", "story_text", "scenes"]


def test_anthropic_tool_uses_story_schema():
    tool = _anthropic_story_tool()

    assert tool["name"] == STORY_DRAFT_TOOL_NAME
    assert tool["input_schema"]["required"] == ["story_summary", "story_text", "scenes"]
    assert tool["input_schema"]["properties"]["scenes"]["items"]["required"] == [
        "title",
        "prompt",
        "subtitle",
        "duration_s",
    ]


def test_extract_anthropic_tool_payload_reads_tool_use_input():
    content = [
        {
            "type": "tool_use",
            "name": STORY_DRAFT_TOOL_NAME,
            "input": {
                "story_summary": "概览",
                "story_text": "正文",
                "scenes": [
                    {
                        "title": "开场",
                        "prompt": "城市清晨",
                        "subtitle": "新的一天开始了",
                        "duration_s": 4,
                    }
                ],
            },
        }
    ]

    payload = _extract_anthropic_tool_payload(content)

    assert payload is not None
    assert payload["story_summary"] == "概览"
