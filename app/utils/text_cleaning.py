"""Text cleaning utilities for OCR output."""

import re
from typing import List


def clean_ocr_text(text: str) -> str:
    """
    Clean OCR-extracted text by removing artifacts and normalizing.

    Args:
        text: Raw OCR text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove artifacts and normalize
    cleaned = remove_artifacts(text)
    cleaned = normalize_whitespace(cleaned)

    return cleaned.strip()


def remove_artifacts(text: str) -> str:
    """
    Remove OCR artifacts and stray characters.

    Args:
        text: Text with potential OCR artifacts

    Returns:
        Text with artifacts removed
    """
    if not text:
        return ""

    # Remove common OCR artifacts
    # Remove control characters except newlines and tabs
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

    # Remove excessive punctuation artifacts
    text = re.sub(r"\.{3,}", "...", text)  # Multiple dots -> ellipsis
    text = re.sub(r"-{3,}", "---", text)  # Multiple dashes -> em dash

    # Remove stray characters that are likely OCR errors
    # Keep common mathematical and special characters
    text = re.sub(
        r"[^\w\s\.\,\;\:\!\?\-\+\=\*\/\(\)\[\]\{\}\<\>\^\$\%\#\@\&\|\\\n\t]", "", text
    )

    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    Args:
        text: Text with potentially irregular whitespace

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""

    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text


def extract_math_expressions(text: str) -> List[str]:
    """
    Extract mathematical expressions from text.

    This is a basic implementation. For production, consider using
    a more sophisticated math expression parser.

    Args:
        text: Text potentially containing mathematical expressions

    Returns:
        List of extracted mathematical expressions
    """
    if not text:
        return []

    # Pattern for common mathematical expressions
    # Matches expressions like: x^2, (a+b), sqrt(x), etc.
    patterns = [
        r"[a-zA-Z]\^[0-9]+",  # Variables with exponents
        r"\([^)]*[+\-*/][^)]*\)",  # Expressions in parentheses
        r"sqrt\([^)]+\)",  # Square root
        r"\\?frac\{[^}]+\}\{[^}]+\}",  # LaTeX fractions
    ]

    expressions = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        expressions.extend(matches)

    return list(set(expressions))  # Remove duplicates
