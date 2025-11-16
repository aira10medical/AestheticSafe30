# services/README.md

## AestheticSafe30 - Services Directory

This directory contains isolated service modules that provide specific functionality without dependencies on the core application modules.

### openai_client.py

Isolated OpenAI client for AestheticSafe30 medical chat functionality.

#### Features
- **Environment-based configuration**: Loads `OPENAI_API_KEY` from environment variables only (never uses `st.secrets`)
- **No Streamlit dependency**: Pure Python module that can be used independently
- **Flexible SDK support**: Works with both modern OpenAI SDK (>=1.x) and legacy versions
- **Model selection**: Uses `OPENAI_MODEL` or `OPENAI_MODEL_OVERRIDE` environment variable, defaults to `gpt-4o-mini`

#### Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key (set in Railway or your hosting environment)

Optional:
- `OPENAI_MODEL`: Preferred model to use (e.g., `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`)
- `OPENAI_MODEL_OVERRIDE`: Alternative model override

#### Usage

```python
from services.openai_client import chat_medic, is_available

# Check if OpenAI is available
if is_available():
    # Send a prompt and get response
    response = chat_medic("What are the symptoms of hypertension?")
    print(response)
else:
    print("OpenAI client not configured")
```

#### API

##### `is_available() -> bool`
Returns `True` if an OpenAI client is available and configured with an API key.

##### `chat_medic(prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> str`
Send a single-turn prompt to OpenAI and return the assistant's response.

Parameters:
- `prompt`: The user's question or prompt
- `temperature`: Sampling temperature (0.0 = deterministic, higher = more random)
- `max_tokens`: Maximum tokens in the response

Returns:
- The assistant's text response, or an error message if something goes wrong

#### Security Notes

✅ **What this module does:**
- Uses environment variables for API key storage
- No hardcoded secrets
- No imports from core modules (calculadora, gsheets, app, pdf_generator)
- Graceful error handling (returns error messages instead of raising exceptions)

❌ **What this module does NOT do:**
- Does not use `st.secrets` or any Streamlit-specific configuration
- Does not modify or import any existing core application modules
- Does not store sensitive data in the codebase

#### Isolation Principles

This module is completely isolated from the core AestheticSafe30 application:
- No dependencies on `calculadora.py`, `gsheets.py`, `app.py`, `pdf_generator_v3_1.py`, or other core modules
- Can be tested independently
- Changes to this module do not affect existing functionality
- Used exclusively by the `pages/1_Chat_Médico.py` Streamlit page
