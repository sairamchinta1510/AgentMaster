import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def stream_llm_json(
    client: AsyncOpenAI,
    model: str,
    messages: list,
    temperature: float = 0.1,
    on_event=None,
    context: str = "",
) -> str:
    """Stream a JSON-mode LLM call, emitting LLM_STREAM events with live token counts."""
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=temperature,
        stream=True,
    )

    full = ""
    token_count = 0
    last_reported = 0

    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full += delta
            token_count += 1  # each chunk ≈ 1 token (good enough for UI display)
            if on_event and token_count - last_reported >= 40:
                await on_event("LLM_STREAM", {"context": context, "tokens": token_count, "text": full[-300:]})
                last_reported = token_count

    # Final flush
    if on_event and token_count > last_reported:
        await on_event("LLM_STREAM", {"context": context, "tokens": token_count, "text": full[-300:]})

    if not full.strip():
        raise ValueError(f"LLM returned empty response for context: {context}")

    try:
        return full
    except Exception:
        logger.error("LLM response for '%s' was not valid JSON (length=%d): %s…", context, len(full), full[:200])
        raise
