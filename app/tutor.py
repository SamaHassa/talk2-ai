"""Tutor logic: conversation state, the reply call and the analysis call."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.llm import LLMClient, Message
from app.prompts import ANALYSIS_SYSTEM, TUTOR_SYSTEM
from app.schemas import CEFR_ORDER, Analysis, LevelEstimate

ANALYSIS_CONTEXT_TURNS = 4  # earlier messages the analyser sees for context


@dataclass
class Session:
    history: list[Message] = field(default_factory=list)
    level_estimates: list[LevelEstimate] = field(default_factory=list)

    @property
    def level(self) -> str | None:
        return aggregate_level(self.level_estimates)


def aggregate_level(estimates: list[LevelEstimate], window: int = 10) -> str | None:
    """Confidence-weighted average of recent per-message CEFR estimates.

    One message is a noisy signal ("hola" says little), so the session level is smoothed
    over the last `window` messages, weighting each by the model's own confidence.
    """
    recent = [e for e in estimates[-window:] if e.confidence > 0]
    if not recent:
        return None
    total = sum(e.confidence for e in recent)
    score = sum(CEFR_ORDER.index(e.cefr) * e.confidence for e in recent) / total
    return CEFR_ORDER[round(score)]


class Tutor:
    def __init__(self, llm: LLMClient, max_history_turns: int = 20):
        self.llm = llm
        self.max_history_turns = max_history_turns
        self.sessions: dict[str, Session] = defaultdict(Session)  # in-memory; step 3 persists it

    def _tutor_system(self, session: Session) -> str:
        return TUTOR_SYSTEM.format(level=session.level or "unknown yet (assume A2 until you learn more)")

    def _analysis_messages(self, session: Session, message: str) -> list[Message]:
        context = session.history[-ANALYSIS_CONTEXT_TURNS:]
        transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in context) or "(start of conversation)"
        return [{
            "role": "user",
            "content": f"<context>\n{transcript}\n</context>\n\n<learner_message>\n{message}\n</learner_message>",
        }]

    def _trimmed(self, history: list[Message]) -> list[Message]:
        trimmed = history[-self.max_history_turns * 2:]
        while trimmed and trimmed[0]["role"] != "user":  # API requires the first message be a user turn
            trimmed = trimmed[1:]
        return trimmed

    def start_analysis(self, session_id: str, message: str) -> "asyncio.Task[Analysis]":
        """Start the grammar/level analysis in the background.

        The prompt is built *now*, before the reply is added to history, so the analyser
        always sees the conversation as it was when the learner sent the message.
        """
        messages = self._analysis_messages(self.sessions[session_id], message)
        return asyncio.create_task(self.llm.parse(ANALYSIS_SYSTEM, messages, Analysis))

    async def reply_stream(self, session_id: str, message: str) -> AsyncIterator[str]:
        session = self.sessions[session_id]
        messages = self._trimmed(session.history + [{"role": "user", "content": message}])
        parts: list[str] = []
        async for chunk in self.llm.stream_text(self._tutor_system(session), messages):
            parts.append(chunk)
            yield chunk
        session.history += [{"role": "user", "content": message}, {"role": "assistant", "content": "".join(parts)}]

    def record_analysis(self, session_id: str, analysis: Analysis) -> None:
        self.sessions[session_id].level_estimates.append(analysis.level)

    async def chat(self, session_id: str, message: str) -> tuple[str, Analysis]:
        """Run the reply and the analysis concurrently, so feedback adds no extra wait."""
        analysis_task = self.start_analysis(session_id, message)
        reply = "".join([c async for c in self.reply_stream(session_id, message)])
        analysis = await analysis_task
        self.record_analysis(session_id, analysis)
        return reply, analysis
