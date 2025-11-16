from typing import Optional
import os
import logging

logger = logging.getLogger("AestheticSafe30.services.openai_client")

_OPENAI_CLIENT = None
_OPENAI_MODE = None

# Try modern client
try:
    from openai import OpenAI  # type: ignore
    _OPENAI_CLIENT = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    _OPENAI_MODE = "modern"
    logger.info("OpenAI client initialized (modern).")
except Exception:
    try:
        import openai  # type: ignore
        if os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        _OPENAI_CLIENT = openai
        _OPENAI_MODE = "legacy"
        logger.info("OpenAI client initialized (legacy).")
    except Exception:
        _OPENAI_CLIENT = None
        _OPENAI_MODE = None
        logger.warning("No OpenAI client available.")


def is_available() -> bool:
    return _OPENAI_CLIENT is not None


def _preferred_model() -> str:
    return (
        os.environ.get("OPENAI_MODEL")
        or os.environ.get("OPENAI_MODEL_OVERRIDE")
        or "gpt-4o-mini"
    )


def chat_medic(prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> str:
    if not _OPENAI_CLIENT:
        return "[OpenAI client not configured — set OPENAI_API_KEY]"

    model = _preferred_model()

    try:
        if _OPENAI_MODE == "modern":
            client = _OPENAI_CLIENT
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return "".join(
                getattr(choice.message, "content", "") or ""
                for choice in resp.choices
            )

        elif _OPENAI_MODE == "legacy":
            client = _OPENAI_CLIENT
            resp = client.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return "".join(
                c.get("message", {}).get("content", "") or ""
                for c in resp.get("choices", [])
            )

        return "[OpenAI client unavailable]"
    except Exception as e:
        logger.exception("Error in chat_medic: %s", e)
        return f"[OpenAI error: {str(e)}]"

