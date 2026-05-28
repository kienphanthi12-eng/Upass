# utils_question_parser.py
"""Helper utilities for extracting answer and explanation tags from a question block.

The DeepSeek pipeline expects the raw markdown to contain tags like:
    [DAPAN: A]
    [LOIGIAI: ...]
These tags may appear anywhere within the question block (often after the
question stem).  This module provides small, pure‑Python helpers to:

* locate a tag and return its inner content (handling multiline explanations),
* optionally remove the tag from the original text, and
* clean up the remaining question text.

The functions are deliberately simple and have no external dependencies –
they can be unit‑tested in isolation.
"""
import re
from typing import Tuple, Optional

# Regex that captures any tag of the form [TAG: content]
_TAG_PATTERN = re.compile(r"\[(?P<tag>[^\]:]+):\s*(?P<content>.*?)\]", re.DOTALL | re.IGNORECASE)


def extract_tag(content: str, tag_name: str) -> Tuple[Optional[str], str]:
    """Extract the first occurrence of a ``[TAG: ...]`` from *content*.

    Args:
        content: The raw markdown for a single question.
        tag_name: Tag identifier, e.g. ``"DAPAN"`` or ``"LOIGIAI"``.

    Returns:
        A tuple ``(value, cleaned_content)`` where *value* is the inner
        text of the tag (``None`` if not found) and *cleaned_content* is the
        original *content* with that tag removed.
    """
    pattern = re.compile(rf"\[{re.escape(tag_name)}:\s*(?P<value>.*?)\]", re.DOTALL | re.IGNORECASE)
    match = pattern.search(content)
    if not match:
        return None, content
    value = match.group("value").strip()
    # Remove the whole tag (including the surrounding brackets) from the text
    start, end = match.span()
    cleaned = (content[:start] + content[end:]).strip()
    return value, cleaned


def clean_question_text(content: str) -> str:
    """Return *content* with any ``[DAPAN:]`` or ``[LOIGIAI:]`` tags stripped.

    The function is tolerant – if a tag is missing it simply returns the
    original string.  It also collapses multiple blank lines into a single
    newline to keep the result tidy.
    """
    _, without_answer = extract_tag(content, "DAPAN")
    cleaned, _ = extract_tag(without_answer, "LOIGIAI")
    # Normalise excessive whitespace – keep at most two consecutive newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
