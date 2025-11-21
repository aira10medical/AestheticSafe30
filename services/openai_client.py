# services/openai_client.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_openai(message: str) -> str:
    """Send a message to the model and return response text."""
    completion = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": message}],
        max_tokens=500,
    )
    return completion.choices[0].message.content
