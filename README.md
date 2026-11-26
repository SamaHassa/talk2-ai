# Talk2 AI: Spanish AI tutor

![CI](https://github.com/SamaHassa/talk2-ai/actions/workflows/ci.yml/badge.svg)

> Status: early prototype (text tutor). The full plan is in [docs/ROADMAP.md](docs/ROADMAP.md); free tool choices are in [docs/FREE_STACK.md](docs/FREE_STACK.md).

Chat in Spanish with **Sofía**, an AI tutor who explains things in English. Every message you
send is also analysed for grammar mistakes and graded on the CEFR scale (A1 to C2), and the
app keeps a running estimate of your level.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then pick a free provider in .env (see below)
uvicorn app.main:app --reload
```

### Free AI providers (pick one in `.env`)

| `TALK2AI_PROVIDER` | Cost | Setup | Good for |
|---|---|---|---|
| `groq` (default) | Free tier with rate limits | Free key from console.groq.com into `GROQ_API_KEY` | Fast replies, which matters for voice later |
| `gemini` | Free tier with rate limits | Free key from aistudio.google.com into `GEMINI_API_KEY` | Strong Spanish, generous context |
| `huggingface` | Free monthly credits | Free token from huggingface.co/settings/tokens into `HF_TOKEN` | Trying many open models (Qwen, Llama, Mistral) by changing `TALK2AI_MODEL` |
| `ollama` | Free, unlimited, runs on your computer | Install from ollama.com, then `ollama pull qwen2.5:7b` | Offline work, no account; slower on a laptop |
| `anthropic` | Paid | `ANTHROPIC_API_KEY` | Optional comparison in the evaluation phase |

All free providers use the OpenAI-compatible API, so one client (`OpenAICompatibleClient`) covers them.
Free-tier limits and model names change, so override the model with `TALK2AI_MODEL` if one is retired.

Open http://localhost:8000 for the chat page, or http://localhost:8000/docs for the API.
Run the tests (offline, no API key needed): `pytest -q`

## How the AI part works

```
learner message ──┬──► Reply call (streamed, temp 0.7)   ──► tokens to the browser
                  │       system prompt adapts to the learner's current level
                  └──► Analysis call (JSON, temp 0)     ──► Analysis JSON
                          corrections + natural rewrite + CEFR estimate
                                         │
                                         ▼
                     confidence-weighted level over the last 10 messages
```

| Concept | Where | Why it matters (and what interviewers ask about) |
|---|---|---|
| **Two specialised LLM calls in parallel** | `app/tutor.py` `chat`, `start_analysis` | Separating "be a good conversation partner" from "be a strict examiner" gives better results for both, and running them concurrently means feedback adds no wait. |
| **Structured outputs with Pydantic** | `app/schemas.py`, `app/llm.py` `parse` | The model's answer is validated against a schema (`Analysis`), so the frontend never has to parse free text. Free models don't always obey a schema, so the client uses a *validate and repair* loop: if Pydantic rejects the JSON, the error is sent back once for the model to fix. Error categories are a fixed enum, which makes them countable and evaluable. |
| **Streaming (SSE)** | `app/main.py` `/chat/stream` | Learners see the reply as it's written; essential later for voice. |
| **Prompt engineering** | `app/prompts.py` | Level-adaptive tutor persona; explicit grading rules to avoid false positives (e.g. not flagging missing `¿` in chat). Prompts live in one file so they can be versioned and evaluated. |
| **Provider abstraction** | `app/llm.py` `LLMClient`, `make_llm` | The app depends on a small interface, so Groq, Gemini, Ollama or a paid model are a one-line config change, and tests use a fake. |
| **Generation parameters** | `app/llm.py` | Chat uses temperature 0.7 for natural variety; grading uses temperature 0 so the same sentence gets the same verdict. |
| **Reliability** | `app/llm.py`, `app/main.py` | Timeouts and automatic retries on the client, invalid-output repair, and provider errors mapped to clean HTTP errors. |
| **Level smoothing** | `app/tutor.py` `aggregate_level` | One message is a noisy signal ("hola" says little), so the session level is a confidence-weighted average. |
| **Tested without the API** | `tests/` | A fake LLM makes tests fast, free and deterministic. |

## Limitations to fix in later steps

- Sessions live in memory and are lost on restart (step 3 adds a database and learner memory).
- No voice yet (step 2).
- We don't yet *measure* how accurate the corrections and level estimates are (step 4 builds an eval set).

## Project structure

```
app/
  config.py     settings from env / .env
  schemas.py    Pydantic models: Correction, LevelEstimate, Analysis, API request/response
  prompts.py    tutor and examiner system prompts
  llm.py        LLMClient interface + Claude implementation
  tutor.py      sessions, the two calls, level aggregation
  main.py       FastAPI routes: /chat, /chat/stream, /health, test page
  static/       minimal chat page
tests/          unit + API tests with a fake LLM
```
