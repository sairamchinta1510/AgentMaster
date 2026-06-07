import json
import logging
import re
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _repair_json_escapes(text: str) -> str:
    r"""Fix invalid content in LLM-generated JSON strings.

    Handles two classes of problems:
    1. Bare backslashes (e.g. \w, C:\Users) — escaped to \\
    2. Literal control characters inside strings (e.g. real newline 0x0A, tab 0x09)
       — replaced with their JSON escape sequences (\n, \t, etc.)

    Uses a state-machine scanner so already-valid escape sequences (\\, \n, \uXXXX)
    are never double-escaped.
    """
    HEX = frozenset('0123456789abcdefABCDEF')
    VALID_SINGLE = frozenset('"\\' + '/bfnrt')
    CONTROL_ESCAPES = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\b': '\\b', '\f': '\\f'}

    result = []
    i = 0
    in_string = False

    while i < len(text):
        c = text[i]

        if not in_string:
            result.append(c)
            if c == '"':
                in_string = True
            i += 1
            continue

        if c == '\\':
            nxt = text[i + 1] if i + 1 < len(text) else ''
            if nxt in VALID_SINGLE:
                # e.g. \\ \" \n \t — keep as-is
                result.append(c)
                result.append(nxt)
                i += 2
            elif nxt == 'u' and i + 5 < len(text) and all(ch in HEX for ch in text[i + 2:i + 6]):
                # Valid \uXXXX unicode escape — keep as-is
                result.append(text[i:i + 6])
                i += 6
            else:
                # Invalid escape — double the backslash to make it valid JSON
                result.append('\\\\')
                i += 1
        elif c == '"':
            in_string = False
            result.append(c)
            i += 1
        elif c in CONTROL_ESCAPES:
            # Literal control character inside a JSON string — escape it
            result.append(CONTROL_ESCAPES[c])
            i += 1
        else:
            result.append(c)
            i += 1

    return ''.join(result)


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
        repaired = _repair_json_escapes(full)
        json.loads(repaired)  # validate before returning
        return repaired
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM response for '%s' was not valid JSON (length=%d) at %s: %s…",
            context, len(full), exc, full[:200],
        )
        raise
