import re
import logging

logger = logging.getLogger(__name__)

# Common PII Regex Patterns
PII_PATTERNS = {
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "phone": re.compile(
        r'\b(?:\+?1[-. ]?)?(?:\(?[2-9][0-8][0-9]\)?[-. ]?)?[2-9][0-9]{2}[-. ]?[0-9]{4}\b'
        r'|\b\d{3}-\d{4}\b'
    ),
    "credit_card": re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "ipv4": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
}

def redact_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Scans text for PII patterns and replaces them with a masking string.
    Useful for cleaning tool outputs (news, web search) before saving to memory.
    """
    if not text:
        return text

    redacted_text = text
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(redacted_text)
        if matches:
            logger.debug(f"Redacting {len(matches)} {pii_type} patterns")
            redacted_text = pattern.sub(replacement, redacted_text)
            
    return redacted_text
