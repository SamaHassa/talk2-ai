"""Settings loaded from environment variables (or a .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TALK2AI_", env_file=".env", extra="ignore")

    # Which LLM backend to use. Free options: "groq" (free API tier, fast), "gemini"
    # (free API tier), "huggingface" (open models, free monthly credits), "ollama" (runs on your own computer, no key, no limits).
    # "anthropic" is a paid option kept for comparison.
    provider: str = "groq"
    # Leave empty to use the provider's default from PROVIDER_PRESETS.
    model: str = ""
    base_url: str = ""
    api_key: str = ""  # or set GROQ_API_KEY / GEMINI_API_KEY; Ollama needs none
    # Effort settings only apply to the paid "anthropic" provider.
    chat_effort: str = "low"
    # Grammar analysis benefits from a bit more thinking; it runs in parallel with the reply.
    analysis_effort: str = "medium"
    max_history_turns: int = 20


# Free-tier model names change often; override with TALK2AI_MODEL if one is retired.
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.5-flash", "key_env": "GEMINI_API_KEY"},
    # Hugging Face Inference Providers router: open models (Qwen, Llama, Mistral...) with a free HF token.
    "huggingface": {"base_url": "https://router.huggingface.co/v1", "model": "Qwen/Qwen2.5-72B-Instruct", "key_env": "HF_TOKEN"},
    "ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b", "key_env": ""},
    "anthropic": {"base_url": "", "model": "claude-opus-5-5", "key_env": "ANTHROPIC_API_KEY"},
}


@lru_cache
def get_settings() -> Settings:
    return Settings()
