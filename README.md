Talk2 AI 🇪🇸
An AI Spanish tutor for English-speaking beginners (CEFR A1). Learners chat with the tutor, by text and later by voice, get their grammar mistakes corrected with explanations in English, and see their level grow over time.

I'm building this project step by step to learn production-grade AI engineering: LLM integration, structured outputs, evaluation, RAG, agents, speech AI and deployment. Everything runs on free tiers and open-source tools.

Status: 🚧 Week 1 of 12. Experimenting with the core AI: grammar correction with an LLM.

What it will do (MVP)
ID	Feature
FR-1	Learner picks a teaching style (Fun, Balanced or Strict) and the tutor adapts
FR-2	CEFR level tracking: move up a level after 30 consistent messages and a passed quiz
FR-3	Voice tutor: speak Spanish and hear the reply (speech-to-text + text-to-speech)
FR-4	Grammar check on every message: mistake, correction, category, English explanation
FR-5	Text conversation with active correction: retry until it's right, depending on the style
Key quality targets: first words of a reply in under 1 second, at least 95% on-topic replies, voice recordings deleted after 48 hours, automatic fallback to a backup AI provider, and $0 running cost.

Tech stack
Layer	Tool	Why
Language	Python	Main language for AI engineering
LLM	Groq free tier (openai/gpt-oss-120b) via the OpenAI-compatible API	Fast and free; the same code works with Gemini, Hugging Face or Ollama
Validation	Pydantic	Forces the AI's answers into a strict, testable shape
API	FastAPI	Async, automatic Swagger docs
Planned	LangGraph, MCP, pgvector, faster-whisper, Piper, Docker, GitHub Actions	Agents, RAG, voice and deployment
Run it locally
git clone https://github.com/SamaHassa/talk2-ai
cd talk2-ai
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
Create a .env file (never committed):

GROQ_API_KEY=your-free-key-from-console.groq.com
GROQ_MODEL=openai/gpt-oss-120b
Try the first experiment:

python experiments/first_call.py
Roadmap (12 weeks)
 Weeks 1-2: Requirements (SRS) ✅, setup ✅, first LLM experiments (in progress)
 Weeks 3-4: LLM core: tutor, structured grammar feedback, streaming, provider fallback
 Week 5: Evaluation: 100 labelled sentences, accuracy against targets
 Weeks 6-7: Memory and RAG: learner profile, mistake history, grammar notes retrieval
 Weeks 8-9: Agent and MCP: LangGraph workflow (tutor, quiz, review) with tools
 Weeks 10-11: Voice: speech-to-text and text-to-speech over WebSockets
 Week 12: Docker, live demo on Hugging Face Spaces
What I've learned so far
Model names change: Groq retired the model I first used, so I now list available models through the API and keep the model name in config, not code.
Measure cost per request: one grammar check uses about 450 tokens, which decides how many checks fit in the free daily limit.
Free text isn't enough for an app: the next step is structured JSON output validated with Pydantic.