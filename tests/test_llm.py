"""Tests for the free-provider client's validate-and-repair structured output loop."""

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.llm import LLMError, OpenAICompatibleClient, make_llm
from app.schemas import LevelEstimate

GOOD = '{"cefr": "A2", "confidence": 0.6, "reasoning": "present tense only"}'
BAD = '{"cefr": "Z9", "confidence": 2}'


class FakeCompletions:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def client_with(replies):
    fake = FakeCompletions(replies)
    llm = OpenAICompatibleClient(Settings(provider="ollama"), client=SimpleNamespace(chat=SimpleNamespace(completions=fake)))
    return llm, fake


@pytest.mark.anyio
async def test_parse_valid_first_time():
    llm, fake = client_with([GOOD])
    out = await llm.parse("sys", [{"role": "user", "content": "hola"}], LevelEstimate)
    assert out.cefr == "A2" and len(fake.calls) == 1
    assert fake.calls[0]["response_format"] == {"type": "json_object"}
    assert '"cefr"' in fake.calls[0]["messages"][0]["content"]  # schema is in the system prompt


@pytest.mark.anyio
async def test_parse_repairs_invalid_json_once():
    llm, fake = client_with([BAD, GOOD])
    out = await llm.parse("sys", [{"role": "user", "content": "hola"}], LevelEstimate)
    assert out.cefr == "A2" and len(fake.calls) == 2
    assert "invalid" in fake.calls[1]["messages"][-1]["content"]


@pytest.mark.anyio
async def test_parse_gives_up_after_two_bad_replies():
    llm, _ = client_with([BAD, "not json"])
    with pytest.raises(LLMError):
        await llm.parse("sys", [{"role": "user", "content": "hola"}], LevelEstimate)


def test_presets_and_unknown_provider():
    llm = make_llm(Settings(provider="groq", api_key="x"))
    assert llm.model == "llama-3.3-70b-versatile"
    hf = make_llm(Settings(provider="huggingface", api_key="x"))
    assert "router.huggingface.co" in str(hf.client.base_url)
    with pytest.raises(ValueError):
        make_llm(Settings(provider="nope"))


@pytest.fixture
def anyio_backend():
    return "asyncio"
