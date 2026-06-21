from typing import Dict, Optional
import google.generativeai as genai
from app.config import settings
from app.utils.metrics import count_tokens

# Configure Gemini (only if API key is provided)
if settings.gemini_api_key and settings.gemini_api_key != "test_api_key":
    genai.configure(api_key=settings.gemini_api_key)


def llm_call_tool(prompt: str, system: Optional[str] = None) -> Dict:
    """
    Call Google Gemini LLM with a prompt.

    Args:
        prompt: The user prompt
        system: Optional system instruction

    Returns:
        dict with status, response, tokens_used, error
    """
    # Check if API key is configured
    if not settings.gemini_api_key or settings.gemini_api_key == "test_api_key":
        return {
            "status": "failed",
            "response": "",
            "tokens_used": 0,
            "error": "GEMINI_API_KEY not configured. Set GEMINI_API_KEY in .env file. Get your key from: https://makersuite.google.com/app/apikey"
        }

    try:
        # Use the correct model name for Gemini API
        # gemini-2.5-flash: Latest fast model
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system if system else None
        )

        response = model.generate_content(prompt)
        response_text = response.text

        # Estimate tokens
        prompt_tokens = count_tokens(prompt)
        response_tokens = count_tokens(response_text)

        return {
            "status": "completed",
            "response": response_text,
            "tokens_used": prompt_tokens + response_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens
        }
    except Exception as e:
        return {
            "status": "failed",
            "response": "",
            "tokens_used": 0,
            "error": str(e)
        }
