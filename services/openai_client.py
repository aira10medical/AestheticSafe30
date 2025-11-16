# services/openai_client.py
"""
Isolated OpenAI client for AestheticSafe30.
- Loads OPENAI_API_KEY from environment variables only.
- Exposes chat_medic(prompt: str) -> str
- Prefers model in OPENAI_MODEL env var or gpt-4o-mini/gpt-4o
- No Streamlit or st.secrets usage
- Robust to modern or legacy openai SDKs
"""
from typing import Optional
import os
import logging

logger = logging.getLogger("AestheticSafe30.services.openai_client")

_OPENAI_CLIENT = None
_OPENAI_MODE = None

# Initialize client if possible (modern OpenAI client or legacy openai package)
try:
    # Modern client (openai>=1.x)
    from openai import OpenAI  # type: ignore
    _OPENAI_CLIENT = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    _OPENAI_MODE = "modern"
    logger.info("OpenAI client initialized (modern OpenAI)")
except Exception:
    try:
        import openai  # type: ignore
        if os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        _OPENAI_CLIENT = openai
        _OPENAI_MODE = "legacy"
        logger.info("OpenAI client initialized (legacy openai package)")
    except Exception:
        _OPENAI_CLIENT = None
        _OPENAI_MODE = None
        logger.warning("OpenAI client not available; OPENAI_API_KEY present: %s", bool(os.environ.get("OPENAI_API_KEY")))


def _preferred_model() -> str:
    return os.environ.get("OPENAI_MODEL") or os.environ.get("OPENAI_MODEL_OVERRIDE") or "gpt-4o-mini"


def chat_medic(prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> str:
    """Send a single-turn prompt to OpenAI and return the assistant text.

    - If no client is configured, return a helpful string (no exception raised).
    - This function is synchronous and returns the full text.
    """
    if not _OPENAI_CLIENT:
        return "[OpenAI client not configured — set OPENAI_API_KEY in environment]"

    model = _preferred_model()

    try:
        if _OPENAI_MODE == "modern":
            client = _OPENAI_CLIENT  # OpenAI(api_key=...)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # Try to extract assistant content robustly
            out = []
            for choice in getattr(resp, "choices", []) or []:
                msg = getattr(choice, "message", None)
                if msg:
                    content = getattr(msg, "content", None) or ""
                    out.append(content)
            return "".join(out) or str(resp)
        elif _OPENAI_MODE == "legacy":
            client = _OPENAI_CLIENT
            resp = client.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # legacy extraction
            choices = resp.get("choices", [])
            texts = []
            for c in choices:
                m = c.get("message", {})
                texts.append(m.get("content", ""))
            return "".join(texts) or str(resp)
        else:
            return "[No OpenAI client available]"
    except Exception as e:
        logger.exception("OpenAI chat_medic error: %s", e)
        return f"[OpenAI error: {str(e)}]"
