"""
AestheticSafe® Automatic Language Detection
Version: 2.0 - HTTP Header Based Detection

Auto-detects user language from:
1. URL parameter (?lang=xx) - highest priority
2. Browser Accept-Language HTTP header
3. Session state (cached)
4. Default: Spanish ('es')

Usage:
    from i18n_auto import detect_language, i18n_label
    
    lang = detect_language()  # Returns 'es', 'en', or 'pt'
    text = i18n_label("Hola", "Hello", "Olá")
"""

import streamlit as st
from typing import Optional, Dict
import re


# ============================================================
# CORE LANGUAGE DETECTION
# ============================================================

def detect_language() -> str:
    """
    Auto-detect user language with fallback priority:
    
    Priority order:
    1. URL parameter (?lang=xx) - manual override
    2. Session state (already detected)
    3. Browser Accept-Language HTTP header
    4. Default: Spanish ('es')
    
    Returns:
        str: Two-letter language code ('es', 'en', 'pt')
    
    Examples:
        >>> detect_language()  # Browser in English
        'en'
        >>> detect_language()  # URL: ?lang=pt
        'pt'
    """
    
    # Priority 1: URL parameter (?lang=xx)
    lang_from_url = _read_lang_from_url()
    if lang_from_url:
        # Set both keys for backward compatibility with calculadora.py
        st.session_state["lang"] = lang_from_url
        st.session_state["idioma"] = lang_from_url.upper()
        return lang_from_url
    
    # Priority 2: Session state (cached from previous detection)
    if "lang" in st.session_state and st.session_state["lang"]:
        return st.session_state["lang"]
    
    # Priority 3: Browser Accept-Language header
    lang_from_browser = _read_lang_from_accept_header()
    if lang_from_browser:
        # Set both keys for backward compatibility
        st.session_state["lang"] = lang_from_browser
        st.session_state["idioma"] = lang_from_browser.upper()
        return lang_from_browser
    
    # Priority 4: Default to Spanish
    default_lang = "es"
    st.session_state["lang"] = default_lang
    st.session_state["idioma"] = default_lang.upper()
    return default_lang


def _read_lang_from_url() -> Optional[str]:
    """
    Read language from URL query parameter (?lang=xx)
    
    Returns:
        Optional[str]: Language code if valid, None otherwise
    """
    try:
        query_params = st.query_params
        
        if "lang" in query_params:
            lang = str(query_params["lang"]).lower().strip()
            
            # Direct match
            if lang in ["es", "en", "pt"]:
                return lang
            
            # Map common variants
            lang_variants = {
                "spa": "es",
                "spanish": "es",
                "español": "es",
                "espanol": "es",
                "eng": "en",
                "english": "en",
                "por": "pt",
                "portuguese": "pt",
                "português": "pt",
                "portugues": "pt",
                "br": "pt",
                "pt-br": "pt"
            }
            
            return lang_variants.get(lang)
    
    except Exception:
        pass
    
    return None


def _read_lang_from_accept_header() -> Optional[str]:
    """
    Read language from browser Accept-Language HTTP header
    
    This method works reliably across all browsers including:
    - Chrome (desktop & mobile)
    - Safari (desktop & iOS)
    - Firefox
    - Edge
    
    Returns:
        Optional[str]: Detected language code ('es', 'en', 'pt') or None
    
    Examples:
        Accept-Language: es-AR,es;q=0.9,en-US;q=0.8 → 'es'
        Accept-Language: en-US,en;q=0.9 → 'en'
        Accept-Language: pt-BR,pt;q=0.9,en;q=0.8 → 'pt'
    """
    try:
        # Check if already detected in this session
        if "browser_lang_detected" in st.session_state:
            return st.session_state["browser_lang_detected"]
        
        # Try to read Accept-Language header via Streamlit context (new API)
        try:
            headers = st.context.headers
            
            if headers and "Accept-Language" in headers:
                accept_lang = headers["Accept-Language"]
                
                # Parse Accept-Language header
                # Format: "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7"
                # We take the first (highest priority) language
                
                primary_lang = accept_lang.split(',')[0].strip()
                
                # Normalize to 2-letter code
                detected_lang = _normalize_language_code(primary_lang)
                
                if detected_lang:
                    # Cache in session state
                    st.session_state["browser_lang_detected"] = detected_lang
                    return detected_lang
        
        except (ImportError, AttributeError, Exception):
            # Fallback: st.context.headers not available (older Streamlit versions)
            # Try the deprecated method as fallback
            try:
                from streamlit.web.server.websocket_headers import _get_websocket_headers
                headers = _get_websocket_headers()
                
                if headers and "Accept-Language" in headers:
                    accept_lang = headers["Accept-Language"]
                    primary_lang = accept_lang.split(',')[0].strip()
                    detected_lang = _normalize_language_code(primary_lang)
                    
                    if detected_lang:
                        st.session_state["browser_lang_detected"] = detected_lang
                        return detected_lang
            except:
                pass
    
    except Exception:
        pass
    
    return None


def _normalize_language_code(raw_lang: str) -> Optional[str]:
    """
    Normalize browser language code to supported two-letter code
    
    Args:
        raw_lang: Raw language code from browser (e.g., 'es-AR', 'en-US', 'pt-BR')
    
    Returns:
        Optional[str]: Normalized code ('es', 'en', 'pt') or None if unsupported
    
    Examples:
        >>> _normalize_language_code('es-AR')
        'es'
        >>> _normalize_language_code('en-US')
        'en'
        >>> _normalize_language_code('pt-BR')
        'pt'
        >>> _normalize_language_code('fr-FR')
        None  # Not supported, will fallback to default
    """
    if not raw_lang:
        return None
    
    # Extract primary language (before hyphen or underscore)
    # Examples: 'es-AR' → 'es', 'en-US' → 'en', 'pt-BR' → 'pt'
    match = re.match(r'^([a-z]{2})', raw_lang.lower())
    
    if not match:
        return None
    
    primary_lang = match.group(1)
    
    # Only support es, en, pt
    if primary_lang in ["es", "en", "pt"]:
        return primary_lang
    
    # Unsupported language - will fallback to default
    return None


# ============================================================
# TRANSLATION HELPERS
# ============================================================

def i18n_label(es: str, en: str, pt: str) -> str:
    """
    Get translated string for current language
    
    This is a helper function compatible with existing calculadora.py code.
    
    Args:
        es: Spanish text
        en: English text
        pt: Portuguese text
    
    Returns:
        str: Text in current language
    
    Example:
        >>> i18n_label("Edad", "Age", "Idade")
        'Edad'  # if current lang is 'es'
    """
    lang = st.session_state.get("lang", "es")
    
    translations = {
        "es": es,
        "en": en,
        "pt": pt
    }
    
    return translations.get(lang, es)


def get_current_language() -> str:
    """
    Get currently detected language
    
    Returns:
        str: Current language code ('es', 'en', 'pt')
    """
    return st.session_state.get("lang", "es")


# ============================================================
# TRANSLATION DICTIONARIES (Optional - for structured translations)
# ============================================================

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "app_title": {
        "es": "AestheticSafe® - Evaluación de Riesgo",
        "en": "AestheticSafe® - Risk Assessment",
        "pt": "AestheticSafe® - Avaliação de Risco"
    },
    "splash_title": {
        "es": "AestheticSafe®",
        "en": "AestheticSafe®",
        "pt": "AestheticSafe®"
    },
    "splash_tagline": {
        "es": "Más allá del riesgo. Hacia la perfección.",
        "en": "Beyond Risk. Toward Perfection.",
        "pt": "Além do Risco. Rumo à Perfeição."
    }
}


def get_translation(key: str, lang: Optional[str] = None) -> str:
    """
    Get translation from TRANSLATIONS dictionary
    
    Args:
        key: Translation key
        lang: Language code (if None, uses current language)
    
    Returns:
        str: Translated string or key if not found
    """
    if lang is None:
        lang = get_current_language()
    
    if key in TRANSLATIONS and lang in TRANSLATIONS[key]:
        return TRANSLATIONS[key][lang]
    
    # Fallback to Spanish
    if key in TRANSLATIONS and "es" in TRANSLATIONS[key]:
        return TRANSLATIONS[key]["es"]
    
    return key


# ============================================================
# DEBUGGING & TESTING
# ============================================================

def debug_language_info() -> Dict[str, str]:
    """
    Get debug information about current language detection
    
    Returns:
        dict: Debug information
    """
    debug_info = {
        "current_lang": st.session_state.get("lang", "not_set"),
        "url_param": _read_lang_from_url() or "not_set",
        "cached_browser_lang": st.session_state.get("browser_lang_detected", "not_detected")
    }
    
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers and "Accept-Language" in headers:
            debug_info["accept_language_header"] = headers["Accept-Language"]
        else:
            debug_info["accept_language_header"] = "not_available"
    except:
        debug_info["accept_language_header"] = "error_reading"
    
    return debug_info


if __name__ == "__main__":
    # Test normalization
    test_cases = [
        ("es-AR", "es"),
        ("es-MX", "es"),
        ("en-US", "en"),
        ("en-GB", "en"),
        ("pt-BR", "pt"),
        ("pt-PT", "pt"),
        ("fr-FR", None),  # Not supported
        ("de-DE", None),  # Not supported
    ]
    
    print("Testing language code normalization:")
    for input_code, expected in test_cases:
        result = _normalize_language_code(input_code)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_code:10} → {result} (expected: {expected})")
    
    print("\nAll tests completed!")
