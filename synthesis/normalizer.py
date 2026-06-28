"""
synthesis/normalizer.py
───────────────────────
Deterministic numeric value normalizer for financial metrics.

Converts human-readable financial strings into raw floats:
    "$85.8B"          → 85_800_000_000.0
    "85.8 billion"    → 85_800_000_000.0
    "$2.18"           → 2.18
    "approximately $84 billion" → 84_000_000_000.0

Returns None for any input that cannot be reliably parsed —
we NEVER guess.  The caller decides how to handle None.
"""

import re
from typing import Optional, Union

# ── Multiplier lookup ───────────────────────────────────────────────────────
# Maps suffix strings (case-insensitive) to their numeric multipliers.
# "B" and "billion" are both 1e9, etc.
_MULTIPLIERS = {
    "t":        1e12,
    "trillion": 1e12,
    "b":        1e9,
    "billion":  1e9,
    "m":        1e6,
    "million":  1e6,
    "k":        1e3,
    "thousand": 1e3,
}

# ── Filler words to strip before parsing ────────────────────────────────────
# These appear in transcript text before numeric values:
#   "We delivered approximately $84 billion in revenue"
#   "strong $84B revenue"
# Stripping them first simplifies the core regex.
_FILLER_WORDS = [
    "approximately", "approx", "about", "around", "roughly",
    "nearly", "over", "under", "strong", "record", "solid",
    "just", "only", "almost", "close to", "more than", "less than",
]

# ── Core extraction regex ───────────────────────────────────────────────────
# Captures:
#   Group 1: optional negative sign
#   Group 2: the numeric part (digits, commas, decimal point)
#   Group 3: optional suffix (B, billion, M, million, T, trillion, K, thousand)
#
# Examples that match:
#   "$85.8B"             → ("-"=None, "85.8",       "B")
#   "$85,800,000,000"    → ("-"=None, "85,800,000,000", None)
#   "85.8 billion"       → ("-"=None, "85.8",       "billion")
#   "-$2.18"             → ("-",     "2.18",        None)
#   "$2.18"              → ("-"=None, "2.18",        None)
_VALUE_REGEX = re.compile(
    r"(-?)\s*\$?\s*"                             # optional sign + dollar sign
    r"(\d[\d,]*(?:\.\d+)?)"                      # digits with optional commas and decimal
    r"\s*"                                        # optional whitespace
    r"(trillion|billion|million|thousand|[tbmk])?" # optional suffix
    r"(?:\s|$|[^a-zA-Z])",                       # word boundary (not followed by letters)
    re.IGNORECASE,
)


def normalize_value(raw: Union[str, float, int, None]) -> Optional[float]:
    """
    Normalize a financial value from various human-readable formats to a float.

    Args:
        raw: The input value.  Can be:
             - Already numeric (int/float) → returned as float directly
             - A string like "$85.8B", "85.8 billion", "$85,800,000,000"
             - None → returns None

    Returns:
        The normalized float value, or None if the input cannot be
        reliably parsed.  We NEVER guess — ambiguous input returns None.

    Examples:
        >>> normalize_value(85800000000)
        85800000000.0
        >>> normalize_value("$85.8B")
        85800000000.0
        >>> normalize_value("approximately $84 billion")
        84000000000.0
        >>> normalize_value("not a number")
        None
    """
    # ── Already numeric ─────────────────────────────────────────────────
    if isinstance(raw, (int, float)):
        return float(raw)

    if raw is None:
        return None

    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    # ── Strip filler words ──────────────────────────────────────────────
    # Case-insensitive removal of common qualifiers that precede values
    # in earnings transcripts.
    lower = text.lower()
    for filler in _FILLER_WORDS:
        lower = lower.replace(filler, " ")
    # Rebuild text preserving any remaining structure but using cleaned version
    text = lower.strip()
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    # ── Attempt regex extraction ────────────────────────────────────────
    match = _VALUE_REGEX.search(text)
    if not match:
        return None

    sign_str = match.group(1)
    num_str = match.group(2)
    suffix_str = match.group(3)

    # Remove commas from the numeric part: "85,800,000,000" → "85800000000"
    num_str = num_str.replace(",", "")

    try:
        value = float(num_str)
    except ValueError:
        return None

    # Apply multiplier if suffix is present
    if suffix_str:
        suffix_key = suffix_str.lower()
        multiplier = _MULTIPLIERS.get(suffix_key)
        if multiplier is None:
            return None  # Unknown suffix — don't guess
        value *= multiplier

    # Apply sign
    if sign_str == "-":
        value = -value

    return value
