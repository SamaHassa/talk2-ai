"""Unit tests with a fake LLM, so they run offline, free and deterministically."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_tutor
from app.schemas import Analysis, Correction, LevelEstimate
from app.tutor import Tutor, aggregate_level


class FakeLLM:
    def __init__(self, level="A2", confidence=0.8):
        self.level, self.confidence = level, confidence
        self.calls: list[tuple[str, list]] = []

    async def stream_text(self, system, messages):
        self.calls.append(("stream", list(messages)))
        for chunk in ["¡Muy ", "bien! ", "¿Y tú?"]:
            yield chunk

    async def parse(self, system, messages, schema):
        self.calls.append(("parse", list(messages)))
        return Analysis(
            is_spanish=True,
            corrections=[Correction(original="yo es", corrected="yo soy", category="verb_conjugation",
                                    explanation="'Ser' in first person is 'soy'.")],
            corrected_message="Yo soy estudiante.",
            level=LevelEstimate(cefr=self.level, confidence=self.confidence, reasoning="Simple present."),
            encouragement="Nice sentence structure!",
        )


def est(cefr, conf=1.0):
    return LevelEstimate(cefr=cefr, confidence=conf, reasoning="")


def test_aggregate_level_weights_by_confidence():
    assert aggregate_level([]) is None
    assert aggregate_level([est("B2")]) == "B2"
    # A low-confidence "hola" (A1, 0.1) barely moves a confident B1 history.
    assert aggregate_level([est("B1"), est("B1"), est("A1", 0.1)]) == "B1"
    assert aggregate_level([est("A2"), est("B2")]) in {"B1"}


@pytest.mark.anyio
async def test_chat_updates_history_and_level():
    llm = FakeLLM()
    tutor = Tutor(llm)
    reply, analysis = await tutor.chat("s1", "Yo es estudiante")
    assert reply == "¡Muy bien! ¿Y tú?"
    assert analysis.corrections[0].corrected == "yo soy"
    s = tutor.sessions["s1"]
    assert [m["role"] for m in s.history] == ["user", "assistant"]
    assert s.level == "A2"


@pytest.mark.anyio
async def test_analysis_sees_only_prior_context_and_new_message():
    llm = FakeLLM()
    tutor = Tutor(llm)
    await tutor.chat("s1", "Hola")
    await tutor.chat("s1", "Me llamo Ana")
    parse_prompt = [c for c in llm.calls if c[0] == "parse"][-1][1][0]["content"]
    assert "<learner_message>\nMe llamo Ana\n</learner_message>" in parse_prompt
    assert "USER: Hola" in parse_prompt


@pytest.mark.anyio
async def test_history_is_trimmed_and_starts_with_user():
    llm = FakeLLM()
    tutor = Tutor(llm, max_history_turns=2)
    for i in range(5):
        await tutor.chat("s1", f"mensaje {i}")
    sent = [c for c in llm.calls if c[0] == "stream"][-1][1]
    assert len(sent) <= 4 and sent[0]["role"] == "user" and sent[-1]["content"] == "mensaje 4"


@pytest.fixture
def client():
    app.dependency_overrides[get_tutor] = lambda: Tutor(FakeLLM())
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_endpoint(client):
    r = client.post("/chat", json={"session_id": "x", "message": "Yo es estudiante"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "¡Muy bien! ¿Y tú?" and body["session_level"] == "A2"


def test_stream_endpoint_emits_tokens_then_analysis(client):
    with client.stream("POST", "/chat/stream", json={"session_id": "x", "message": "Hola"}) as r:
        raw = "".join(r.iter_text())
    events = [e.split("\n") for e in raw.strip().split("\n\n")]
    types = [e[0].removeprefix("event: ") for e in events]
    assert types == ["token", "token", "token", "analysis", "done"]
    analysis = json.loads(events[3][1].removeprefix("data: "))
    assert analysis["analysis"]["level"]["cefr"] == "A2"


def test_rejects_empty_message(client):
    assert client.post("/chat", json={"session_id": "x", "message": ""}).status_code == 422


@pytest.fixture
def anyio_backend():
    return "asyncio"
