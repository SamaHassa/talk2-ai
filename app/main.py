"""FastAPI app: JSON and streaming (Server-Sent Events) chat endpoints plus a test page."""

import json
import logging
from functools import lru_cache
from pathlib import Path

import anthropic
import openai
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.config import get_settings
from app.llm import LLMError, make_llm
from app.schemas import ChatRequest, ChatResponse
from app.tutor import Tutor

log = logging.getLogger("talk2ai")
app = FastAPI(title="Talk2 Ai", description="Spanish AI tutor with grammar feedback and CEFR level analysis")
STATIC = Path(__file__).parent / "static"


@lru_cache
def get_tutor() -> Tutor:
    settings = get_settings()
    return Tutor(make_llm(settings), max_history_turns=settings.max_history_turns)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, tutor: Tutor = Depends(get_tutor)) -> ChatResponse:
    try:
        reply, analysis = await tutor.chat(req.session_id, req.message)
    except LLMError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (anthropic.APIError, openai.APIError) as e:
        log.exception("LLM API error")
        raise HTTPException(status_code=502, detail="The AI service is unavailable, try again.") from e
    return ChatResponse(reply=reply, analysis=analysis, session_level=tutor.sessions[req.session_id].level)


def sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, tutor: Tutor = Depends(get_tutor)) -> StreamingResponse:
    """Streams the tutor's reply token by token, then sends the analysis when it is ready.

    Events: `token` (text chunk), `analysis` (Analysis JSON + session level), `error`, `done`.
    """

    async def events():
        analysis_task = tutor.start_analysis(req.session_id, req.message)
        try:
            async for chunk in tutor.reply_stream(req.session_id, req.message):
                yield sse("token", chunk)
            analysis = await analysis_task
            tutor.record_analysis(req.session_id, analysis)
            yield sse("analysis", {
                "analysis": analysis.model_dump(),
                "session_level": tutor.sessions[req.session_id].level,
            })
        except (LLMError, anthropic.APIError, openai.APIError) as e:
            log.exception("chat stream failed")
            analysis_task.cancel()
            yield sse("error", str(e) if isinstance(e, LLMError) else "The AI service is unavailable, try again.")
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream")
