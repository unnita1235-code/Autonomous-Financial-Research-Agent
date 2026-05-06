"""
app/limiter.py
──────────────
Provides the slowapi rate limiter instance.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter. In production, this should be configured with a Redis backend.
limiter = Limiter(key_func=get_remote_address)
