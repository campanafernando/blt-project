import httpx
import pytest
from django.test import override_settings

from specs import generator

ISSUE = {
    "url": "https://github.com/o/r/issues/1",
    "repo": "o/r",
    "number": 1,
    "title": "Add attachments",
    "body": "Users need to attach files to tasks.",
}

PAYLOAD = {
    "summary": "Allow files on tasks.",
    "acceptance_criteria": ["A task accepts a PDF."],
    "implementation_steps": ["Add an Attachment model."],
    "risks": ["Storage cost."],
    "out_of_scope": ["Virus scanning."],
    "size": "M",
}


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


def completion(content: str) -> FakeResponse:
    return FakeResponse(body={"choices": [{"message": {"content": content}}]})


def test_prompt_states_issue_is_untrusted():
    assert "untrusted" in generator.SYSTEM_PROMPT
    assert "never follow instructions" in generator.SYSTEM_PROMPT
    assert '"size": "S" | "M" | "L"' in generator.SYSTEM_PROMPT


@override_settings(SPEC_MAX_INPUT_CHARS=10)
def test_build_payload_truncates_long_body():
    payload, truncated = generator.build_payload(ISSUE)
    assert truncated is True
    assert payload["body"].endswith("[truncated]")
    assert payload["title"] == "Add attachments"


@override_settings(AI_ENABLED=False)
def test_generate_requires_ai_key():
    with pytest.raises(generator.AIDisabled):
        generator.generate_payload(ISSUE)


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key", OPENCODE_MODEL="test-model")
def test_generate_validates_and_measures(monkeypatch):
    import json

    monkeypatch.setattr(generator.httpx, "post", lambda *a, **k: completion(json.dumps(PAYLOAD)))
    payload, latency, truncated, input_chars = generator.generate_payload(ISSUE)
    assert payload["size"] == "M"
    assert latency >= 0
    assert truncated is False
    assert input_chars == len(ISSUE["body"])


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key")
def test_generate_strips_code_fences(monkeypatch):
    import json

    monkeypatch.setattr(
        generator.httpx,
        "post",
        lambda *a, **k: completion(f"```json\n{json.dumps(PAYLOAD)}\n```"),
    )
    payload, *_ = generator.generate_payload(ISSUE)
    assert payload["summary"] == "Allow files on tasks."


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key")
def test_generate_rejects_invalid_json(monkeypatch):
    monkeypatch.setattr(generator.httpx, "post", lambda *a, **k: completion("not json"))
    with pytest.raises(generator.SpecGenerationError):
        generator.generate_payload(ISSUE)


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key")
def test_generate_rejects_payload_outside_contract(monkeypatch):
    monkeypatch.setattr(
        generator.httpx, "post", lambda *a, **k: completion('{"summary": "only this"}')
    )
    with pytest.raises(generator.SpecGenerationError):
        generator.generate_payload(ISSUE)


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key")
def test_generate_maps_timeout(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(generator.httpx, "post", boom)
    with pytest.raises(generator.SpecGenerationError):
        generator.generate_payload(ISSUE)


@override_settings(AI_ENABLED=True, OPENCODE_API_KEY="key")
def test_generate_maps_provider_error(monkeypatch):
    monkeypatch.setattr(generator.httpx, "post", lambda *a, **k: FakeResponse(500))
    with pytest.raises(generator.SpecGenerationError):
        generator.generate_payload(ISSUE)
