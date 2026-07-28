"""Defang IOCs so generated reports never contain live malicious links.
Applied at output time only; the evidence store keeps verbatim values."""

import re

_URL_SCHEME = re.compile(r"\bhttp(s?)://", re.IGNORECASE)
# domain-ish tokens (incl. IPs): defang the dots
_DOTTED = re.compile(
    r"\b((?:[a-zA-Z0-9-]+\.)+(?:[a-zA-Z]{2,}|[0-9]{1,3}))\b"
)


def _bracket_dots(match: re.Match) -> str:
    return match.group(1).replace(".", "[.]")


def defang(text: str) -> str:
    text = _URL_SCHEME.sub(lambda m: f"hxxp{m.group(1)}://", text)
    text = _DOTTED.sub(_bracket_dots, text)
    text = text.replace("@", "[at]")
    return text
