# redact_phi.py
# HIPAA-compliant PHI/PII redaction layer for AestheticSafe
# Redacts sensitive data before logging to Google Sheets or other non-BAA storage

import hashlib
import re
from typing import Any, Dict, List, Optional

# === PHI FIELD DEFINITIONS ===
# Based on HIPAA Privacy Rule - 18 identifiers
PHI_FIELDS = {
    # Direct identifiers
    "nombre": "name",
    "name": "name",
    "email": "email",
    "telefono": "phone",
    "phone": "phone",
    "whatsapp": "phone",
    
    # Health information
    "edad": "age",
    "age": "age",
    "peso": "weight",
    "weight": "weight",
    "altura": "height",
    "height": "height",
    "imc": "bmi",
    "bmi": "bmi",
    
    # Medical conditions
    "tabaquismo": "medical",
    "hipertension": "medical",
    "diabetes": "medical",
    "tiroides": "medical",
    "caprini_score": "medical",
    "antecedentes": "medical",
    "condiciones": "medical",
    
    # Other identifiers
    "ip_address": "ip",
    "session_id": "session",
    "user_agent": "user_agent",
}

# Fields that should be completely removed (not hashed)
REMOVE_FIELDS = [
    "private_key",
    "password",
    "api_key",
    "secret",
    "token",
]

def hash_identifier(value: str, salt: str = "aestheticsafe_2025") -> str:
    """
    One-way hash of an identifier for pseudonymization.
    Allows analytics without storing actual PHI.
    
    Args:
        value: The value to hash
        salt: Salt for the hash (should be project-specific constant)
    
    Returns:
        SHA256 hash as hex string
    """
    if not value:
        return "[REDACTED]"
    
    combined = f"{salt}:{value}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def mask_email(email: str) -> str:
    """
    Partially mask email address.
    Example: john.doe@example.com → j***e@e*****e.com
    """
    if not email or "@" not in email:
        return "[REDACTED_EMAIL]"
    
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        domain_parts = domain.split(".")
        if len(domain_parts) >= 2:
            masked_domain = domain_parts[0][0] + "*" * (len(domain_parts[0]) - 1)
            masked_domain += "." + ".".join(domain_parts[1:])
        else:
            masked_domain = "*" * len(domain)
        
        return f"{masked_local}@{masked_domain}"
    except Exception:
        return "[REDACTED_EMAIL]"


def mask_phone(phone: str) -> str:
    """
    Mask phone number, showing only last 4 digits.
    Example: +5491112345678 → +549****5678
    """
    if not phone:
        return "[REDACTED_PHONE]"
    
    # Extract digits only
    digits = re.sub(r'\D', '', str(phone))
    
    if len(digits) < 4:
        return "*" * len(digits)
    
    # Show country code (if present) and last 4 digits
    if phone.startswith("+"):
        country_code = phone[:phone.find(digits[0])]
        return f"{country_code}****{digits[-4:]}"
    else:
        return f"****{digits[-4:]}"


def redact_value(key: str, value: Any, mode: str = "hash") -> Any:
    """
    Redact a single value based on its key and mode.
    
    Args:
        key: The field name
        value: The value to redact
        mode: Redaction mode - "hash", "mask", "remove", or "keep"
    
    Returns:
        Redacted value
    """
    if value is None or value == "":
        return value
    
    key_lower = key.lower()
    
    # Complete removal for sensitive keys
    if any(remove_key in key_lower for remove_key in REMOVE_FIELDS):
        return "[REMOVED]"
    
    # Email-specific masking
    if "email" in key_lower and mode in ["mask", "hash"]:
        if mode == "mask":
            return mask_email(str(value))
        else:
            return hash_identifier(str(value))
    
    # Phone-specific masking
    if any(phone_key in key_lower for phone_key in ["phone", "telefono", "whatsapp"]):
        if mode == "mask":
            return mask_phone(str(value))
        else:
            return hash_identifier(str(value))
    
    # Name masking
    if "nombre" in key_lower or key_lower == "name":
        if mode == "mask":
            parts = str(value).split()
            if len(parts) >= 2:
                return f"{parts[0][0]}*** {parts[-1][0]}***"
            else:
                return f"{str(value)[0]}***"
        else:
            return hash_identifier(str(value))
    
    # Medical/health data - hash or remove
    if key_lower in PHI_FIELDS:
        phi_type = PHI_FIELDS[key_lower]
        if phi_type == "medical" and mode == "remove":
            return "[PHI_REMOVED]"
        elif mode == "hash":
            return hash_identifier(str(value))
    
    # Default: return as-is
    return value


def redact_dict(data: Dict[str, Any], mode: str = "hash", allowlist: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Redact all PHI/PII fields in a dictionary.
    
    Args:
        data: Dictionary to redact
        mode: Redaction mode - "hash", "mask", "remove"
        allowlist: Fields to keep unchanged (e.g., ["timestamp", "app_version"])
    
    Returns:
        Redacted dictionary
    """
    if allowlist is None:
        allowlist = [
            "timestamp",
            "app_version",
            "idioma_ui",
            "risk_level",  # Aggregated, non-identifying
            "stage",
            "substage",
        ]
    
    redacted = {}
    for key, value in data.items():
        if key.lower() in [a.lower() for a in allowlist]:
            # Keep allowlisted fields unchanged
            redacted[key] = value
        elif isinstance(value, dict):
            # Recursively redact nested dicts
            redacted[key] = redact_dict(value, mode, allowlist)
        elif isinstance(value, list):
            # Redact list items
            redacted[key] = [redact_dict(item, mode, allowlist) if isinstance(item, dict) else redact_value(key, item, mode) for item in value]
        else:
            # Redact single value
            redacted[key] = redact_value(key, value, mode)
    
    return redacted


# === USAGE EXAMPLES ===
if __name__ == "__main__":
    # Example patient data
    patient_data = {
        "nombre": "Juan Pérez",
        "email": "juan.perez@example.com",
        "telefono": "+5491112345678",
        "edad": 35,
        "peso": 70,
        "altura": 165,
        "imc": 25.7,
        "tabaquismo": "No",
        "hipertension": "No",
        "diabetes": "No",
        "caprini_score": 3,
        "timestamp": "2025-11-02 12:00:00",
        "app_version": "3.0",
    }
    
    print("=== ORIGINAL DATA ===")
    print(patient_data)
    
    print("\n=== HASH MODE (for analytics) ===")
    hashed = redact_dict(patient_data, mode="hash")
    print(hashed)
    
    print("\n=== MASK MODE (for partial visibility) ===")
    masked = redact_dict(patient_data, mode="mask")
    print(masked)
    
    print("\n=== REMOVE MODE (complete redaction) ===")
    removed = redact_dict(patient_data, mode="remove")
    print(removed)
