from typing import Dict, Optional
import google.generativeai as genai
from app.config import settings
from app.utils.metrics import count_tokens

# Configure Gemini
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
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
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
