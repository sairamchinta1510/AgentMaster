from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import sys


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentmaster.db"
    gemini_api_key: Optional[str] = None
    log_level: str = "info"
    max_recursion_depth: int = 5
    max_agent_timeout: int = 300
    websocket_ping_interval: int = 30

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Validate API key on startup
if not settings.gemini_api_key or settings.gemini_api_key == "test_api_key":
    print("\n" + "="*70)
    print("⚠️  WARNING: GEMINI_API_KEY not configured!")
    print("="*70)
    print("\nAgentMaster requires a Google Gemini API key for LLM-based agents.")
    print("\nTo fix this:")
    print("  1. Get an API key from: https://makersuite.google.com/app/apikey")
    print("  2. Create a .env file in backend_new/")
    print("  3. Add: GEMINI_API_KEY=your_api_key_here")
    print("\nWithout an API key:")
    print("  ✅ REST API and WebSockets will work")
    print("  ✅ Database operations will work")
    print("  ❌ LLM-based Atomic Agents will fail critique (human review needed)")
    print("  ❌ Complex tasks requiring LLM calls will not complete")
    print("\n" + "="*70 + "\n")
