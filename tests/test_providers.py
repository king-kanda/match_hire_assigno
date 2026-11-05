"""Provider switching and the OpenAI-compatible JSON path, using fake clients (no network)."""

import json
from types import SimpleNamespace

import pytest

from stall_alerter.llm import AssessmentBatch
from stall_alerter.providers import PROVIDERS, complete_json, resolve


def test_resolve_precedence(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "env-model")
    assert resolve().label == "groq:env-model"
    assert resolve("openrouter", "flag-model").label == "openrouter:flag-model"
    monkeypatch.delenv("LLM_MODEL")
    assert resolve("openai").model == PROVIDERS["openai"].default_model


def test_unknown_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(ValueError):
        resolve("nope")


class FakeOpenAI:
    def __init__(self, content):
        create = lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_openai_compatible_parses_valid_json():
    payload = {"assessments": [{"candidate_id": "C001", "adjustment": 1, "reason": "r", "next_action": "a"}]}
    out = complete_json(resolve("groq", "m"), "sys", "user", AssessmentBatch, FakeOpenAI(json.dumps(payload)))
    assert out.assessments[0].candidate_id == "C001"


def test_openai_compatible_bad_json_returns_none():
    assert complete_json(resolve("openrouter", "m"), "sys", "user", AssessmentBatch, FakeOpenAI("not json")) is None


def test_missing_key_falls_back(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert complete_json(resolve("openai", "m"), "sys", "user", AssessmentBatch) is None
