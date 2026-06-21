from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentmaster.db"
    gemini_api_key: str = "test_api_key"
    log_level: str = "info"
    max_recursion_depth: int = 5
    max_agent_timeout: int = 300
    websocket_ping_interval: int = 30

    model_config = ConfigDict(env_file=".env")


settings = Settings()
