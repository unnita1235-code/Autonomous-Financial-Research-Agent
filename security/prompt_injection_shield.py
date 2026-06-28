import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Heuristic-based malicious patterns
MALICIOUS_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system override",
    r"forget what you were told",
    r"you are now a (different agent|unrestricted|malicious)",
    r"output the system prompt",
    r"reveal your (secret|internal) (instructions|prompt)",
    r"execute (arbitrary )?code",
    r"bypass (all )?restrictions",
]

class InjectionShield:
    """
    Detects and prevents prompt injection attacks in user queries.
    """
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in MALICIOUS_PATTERNS]

    def is_safe(self, query: str) -> bool:
        """
        Checks if a query contains known prompt injection patterns.
        """
        for pattern in self.patterns:
            if pattern.search(query):
                logger.warning(f"Possible prompt injection detected in query: {query}")
                return False
        return True

    def sanitize(self, query: str) -> str:
        """
        Removes potentially harmful sequences from a query.
        """
        # Simple sanitization: strip common injection markers
        sanitized = query
        for pattern in self.patterns:
            sanitized = pattern.sub("[FILTERED]", sanitized)
        return sanitized

shield = InjectionShield()
