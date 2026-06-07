from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini (preferred)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # OpenAI (fallback)
    openai_api_key: str = ""

    database_url: str = "sqlite:///./agentmaster.db"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def active_api_key(self) -> str:
        return self.gemini_api_key or self.openai_api_key

    @property
    def active_model(self) -> str:
        if self.gemini_api_key:
            return self.gemini_model
        return "gpt-4o"

    @property
    def active_base_url(self) -> str | None:
        if self.gemini_api_key:
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return None  # use default OpenAI URL


settings = Settings()
