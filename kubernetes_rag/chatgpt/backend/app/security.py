"""Security guardrails for chat input/context handling."""

from __future__ import annotations

import re
from typing import Tuple


# Common prompt-injection and role-confusion patterns.
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|prior) instructions?",
    r"reveal (the )?(system|developer) prompt",
    r"you are now",
    r"act as",
    r"jailbreak",
    r"\bDAN\b",
    r"<\s*(system|developer)\s*>",
    r"override (security|guardrails?)",
    r"tool call",
]

# Patterns that indicate direct secret exfiltration attempts.
SECRETS_EXFIL_PATTERNS = [
    r"(show|reveal|dump|print|expose).*(api[_ -]?key|token|secret|password|credential)",
    r"(api[_ -]?key|token|secret|password|credential).*(show|reveal|dump|print|expose)",
]


def sanitize_text(text: str, max_chars: int = 8000) -> str:
    """Sanitize user/plugin text before LLM usage."""
    if not text:
        return ""
    # Remove control chars that can confuse parsers/prompts.
    cleaned = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
    cleaned = cleaned.strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    return cleaned


def classify_user_message(message: str) -> Tuple[bool, bool]:
    """Return (looks_like_prompt_injection, looks_like_secret_exfil)."""
    msg = message or ""
    has_injection = any(
        re.search(pattern, msg, flags=re.IGNORECASE | re.DOTALL)
        for pattern in PROMPT_INJECTION_PATTERNS
    )
    has_secret_exfil = any(
        re.search(pattern, msg, flags=re.IGNORECASE | re.DOTALL)
        for pattern in SECRETS_EXFIL_PATTERNS
    )
    return has_injection, has_secret_exfil

