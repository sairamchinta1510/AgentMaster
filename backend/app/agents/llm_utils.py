import json
import logging
import re
from json_repair import repair_json
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _repair_json_escapes(text: str) -> str:
    r"""Fix invalid content in LLM-generated JSON strings.

    Uses json-repair as the primary fixer (handles unescaped quotes, missing
    commas, control characters, etc.), with our custom state-machine as a
    pre-processing step for raw backslash escapes that confuse json-repair.
    """
    # Pre-process: fix bare backslashes and literal control chars (our state machine)
    text = _fix_raw_escapes(text)
    # Full structural repair via json-repair library
    return repair_json(text, ensure_ascii=False)


def _fix_raw_escapes(text: str) -> str:
    r"""Pre-processing pass: fix bare backslashes and literal control characters."""
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
                result.append(c)
                result.append(nxt)
                i += 2
            elif nxt == 'u' and i + 5 < len(text) and all(ch in HEX for ch in text[i + 2:i + 6]):
                result.append(text[i:i + 6])
                i += 6
            else:
                result.append('\\\\')
                i += 1
        elif c == '"':
            in_string = False
            result.append(c)
            i += 1
        elif c in CONTROL_ESCAPES:
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

    repaired = _repair_json_escapes(full)
    # json-repair always returns parseable JSON; validate to surface any remaining issues
    try:
        json.loads(repaired)
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM response for '%s' still invalid after repair (length=%d): %s — %s…",
            context, len(full), exc, full[:200],
        )
        raise
    return repaired
