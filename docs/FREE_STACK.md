# Free technology choices for the roadmap

Everything below has a free option. Hosted free tiers have rate limits and can change, so each
choice keeps a fully local fallback.

| Roadmap layer | Free choice | Local fallback |
|---|---|---|
| LLM | Groq, Google Gemini, or Hugging Face Inference Providers (open models, free credits) | Ollama (Qwen 2.5, Llama 3.x) |
| Embeddings | sentence-transformers (e.g. multilingual-e5) run locally | same |
| Vector DB | PostgreSQL + pgvector in Docker | same |
| BM25 / reranking | rank-bm25, a cross-encoder from Hugging Face | same |
| Orchestration | LangGraph, MCP Python SDK (open source) | same |
| Speech-to-text | faster-whisper (local), or Groq's free Whisper endpoint | faster-whisper |
| Text-to-speech | Piper (local, has Spanish voices) | same |
| VAD | Silero VAD | same |
| Pronunciation | wav2vec2 phoneme models from Hugging Face | same |
| Data / queue | PostgreSQL, Redis, Celery in Docker Compose | same |
| Observability | Langfuse self-hosted in Docker (or its free cloud tier) | self-hosted |
| CI/CD | GitHub Actions (free for public repos) | — |
| Demo hosting | Hugging Face Spaces free tier | run locally |

Trade-off to note in an ADR: local models are free but need a reasonably powerful computer and
are slower; hosted free tiers are fast but rate-limited and can't be relied on for production.
