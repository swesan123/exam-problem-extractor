"""Utilities for error handling and sanitization."""

import re
from typing import Any, Dict


def sanitize_error_message(error_message: str, is_production: bool = False) -> str:
    """
    Sanitize error messages to prevent exposing sensitive information.

    Args:
        error_message: Original error message
        is_production: Whether running in production mode

    Returns:
        Sanitized error message safe to return to clients
    """
    if not is_production:
        # In development, return full error for debugging
        return error_message

    # Patterns to redact
    patterns = [
        (
            r"sk-[a-zA-Z0-9]{10,}",
            "sk-***",
        ),  # OpenAI API keys (minimum 10 chars after sk-)
        (r"api[_-]?key[=:]\s*[a-zA-Z0-9_-]+", "api_key=***", re.IGNORECASE),
        (r"password[=:]\s*[^\s]+", "password=***", re.IGNORECASE),
        (r"token[=:]\s*[a-zA-Z0-9_-]+", "token=***", re.IGNORECASE),
        (r"secret[=:]\s*[^\s]+", "secret=***", re.IGNORECASE),
    ]

    sanitized = error_message
    for pattern in patterns:
        if isinstance(pattern, tuple):
            sanitized = re.sub(
                pattern[0],
                pattern[1],
                sanitized,
                flags=pattern[2] if len(pattern) > 2 else 0,
            )
        else:
            sanitized = re.sub(pattern[0], pattern[1], sanitized)

    # Remove file paths that might expose system structure
    sanitized = re.sub(r"/[^\s]+\.(py|db|log|txt)", "***", sanitized)

    # Generic error message if too much was redacted
    if sanitized != error_message and len(sanitized.strip()) < 10:
        return "An internal error occurred. Please try again later."

    return sanitized


def get_safe_error_detail(error: Exception, is_production: bool = False) -> str:
    """
    Get a safe error detail message for client responses.

    Args:
        error: The exception that occurred
        is_production: Whether running in production mode

    Returns:
        Safe error message for clients
    """
    error_str = str(error)
    sanitized = sanitize_error_message(error_str, is_production)

    # If in production and error is too technical, return generic message
    if is_production:
        technical_indicators = [
            "traceback",
            'file "',
            "line ",
            "module",
            "import",
            "attributeerror",
            "typeerror",
        ]
        if any(indicator in error_str.lower() for indicator in technical_indicators):
            return "An internal error occurred. Please try again later."

    return sanitized
