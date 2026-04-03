from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM provider selector: groq | openai | google
    llm_provider: str = "groq"

    # --- Groq (set when LLM_PROVIDER=groq) ---
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: int = 30

    # --- OpenAI (set when LLM_PROVIDER=openai) ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 30

    # --- Google Gemini (set when LLM_PROVIDER=google) ---
    google_api_key: str | None = None
    google_model: str = "gemini-2.0-flash"
    google_timeout_seconds: int = 30

    # External backend base URL (required — set via BACKEND_BASE_URL in .env)
    backend_base_url: str = ""

    # Server
    port: int = 8080


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
