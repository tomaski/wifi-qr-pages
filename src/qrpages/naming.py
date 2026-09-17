"""Output file naming: SSID-comment.pdf, spaces replaced with underscores."""

from __future__ import annotations

import re

UNSAFE = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")


def _slug(text: str) -> str:
    text = WHITESPACE.sub("_", text.strip())
    text = UNSAFE.sub("_", text)
    return text.strip("._") or "unnamed"


def pdf_filename(ssid: str, comment: str | None = None) -> str:
    """Return `SSID-comment.pdf`, or `SSID.pdf` when there is no comment."""
    stem = _slug(ssid)
    if comment and comment.strip():
        stem = f"{stem}-{_slug(comment)}"
    return f"{stem[:200]}.pdf"


def unique_filename(name: str, taken: set[str]) -> str:
    """Disambiguate *name* against already used names by appending -2, -3, ..."""
    if name not in taken:
        taken.add(name)
        return name
    stem = name[: -len(".pdf")]
    counter = 2
    while f"{stem}-{counter}.pdf" in taken:
        counter += 1
    unique = f"{stem}-{counter}.pdf"
    taken.add(unique)
    return unique
