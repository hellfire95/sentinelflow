"""Deterministic .eml parser. No LLM involvement anywhere in this module.

Extracts headers, authentication results, routing, URLs, and attachments as
Evidence objects with stable IDs. Also emits *derived* facts (e.g. domain
mismatches) that are pure string comparisons — deterministic, not judgment.
"""

import hashlib
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Evidence, EvidenceCategory
from .common import EvidenceBuilder

_AUTH_RESULT = re.compile(r"\b(spf|dkim|dmarc)\s*=\s*(\w+)", re.IGNORECASE)
_AUTH_PROP = re.compile(r"\b(smtp\.mailfrom|header\.d|header\.from)\s*=\s*([^\s;]+)")
_TEXT_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

MAX_URL_EVIDENCE = 30  # cap so a link-heavy email can't flood the store


def _domain_of_address(addr: str) -> str:
    return addr.rsplit("@", 1)[-1].lower().strip("<> ") if "@" in addr else ""


def _domain_of_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def parse_eml(path: str, case_id: str) -> list[Evidence]:
    with open(path, "rb") as f:
        msg: EmailMessage = BytesParser(policy=policy.default).parse(f)

    b = EvidenceBuilder(case_id)
    _extract_core_headers(msg, b)
    _extract_authentication(msg, b)
    _extract_routing(msg, b)
    _extract_derived_header_facts(msg, b)
    _extract_body_urls(msg, b)
    _extract_attachments(msg, b)
    return b.items


def _extract_core_headers(msg: EmailMessage, b: EvidenceBuilder) -> None:
    for header in ("From", "Reply-To", "Return-Path", "Sender", "To", "Subject", "Date", "Message-Id"):
        value = msg.get(header)
        if value:
            b.add(EvidenceCategory.HEADER, f"{header} header", str(value), f"header:{header}")


def _extract_authentication(msg: EmailMessage, b: EvidenceBuilder) -> None:
    auth = msg.get("Authentication-Results")
    if auth:
        auth = str(auth)
        for mech, result in _AUTH_RESULT.findall(auth):
            b.add(
                EvidenceCategory.AUTHENTICATION,
                f"{mech.upper()} result",
                result.lower(),
                "header:Authentication-Results",
            )
        for prop, value in _AUTH_PROP.findall(auth):
            b.add(
                EvidenceCategory.AUTHENTICATION,
                f"Authentication property {prop}",
                value,
                "header:Authentication-Results",
            )
    received_spf = msg.get("Received-SPF")
    if received_spf:
        b.add(
            EvidenceCategory.AUTHENTICATION,
            "Received-SPF header",
            str(received_spf),
            "header:Received-SPF",
        )


def _extract_routing(msg: EmailMessage, b: EvidenceBuilder) -> None:
    received = msg.get_all("Received") or []
    b.add(EvidenceCategory.ROUTING, "Received hop count", str(len(received)), "headers:Received")
    if received:
        # The last Received header is the earliest hop: the origin server.
        b.add(
            EvidenceCategory.ROUTING,
            "Earliest Received hop (origin server)",
            " ".join(str(received[-1]).split()),
            f"header:Received[{len(received) - 1}]",
        )
    sender_ip = msg.get("X-Sender-IP")
    if sender_ip:
        b.add(EvidenceCategory.ROUTING, "X-Sender-IP", str(sender_ip), "header:X-Sender-IP")


def _extract_derived_header_facts(msg: EmailMessage, b: EvidenceBuilder) -> None:
    """Pure string comparisons between sender-identity domains."""
    from_domain = _domain_of_address(parseaddr(str(msg.get("From", "")))[1])
    if not from_domain:
        return
    for header in ("Reply-To", "Return-Path", "Sender"):
        raw = msg.get(header)
        if not raw:
            continue
        other = _domain_of_address(parseaddr(str(raw))[1])
        if other and other != from_domain:
            b.add(
                EvidenceCategory.HEADER,
                f"Domain mismatch: From vs {header}",
                f"From domain '{from_domain}' != {header} domain '{other}'",
                f"derived:From,{header}",
            )


def _extract_body_urls(msg: EmailMessage, b: EvidenceBuilder) -> None:
    urls: list[tuple[str, str, str]] = []  # (url, anchor_text, source)

    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/html":
            try:
                soup = BeautifulSoup(part.get_content(), "html.parser")
            except Exception:
                continue
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.lower().startswith(("http://", "https://")):
                    urls.append((href, a.get_text(strip=True), "body:html:a[href]"))
        elif ctype == "text/plain":
            try:
                text = part.get_content()
            except Exception:
                continue
            for m in _TEXT_URL.findall(text):
                urls.append((m, "", "body:text"))

    seen: set[str] = set()
    count = 0
    for url, anchor, source in urls:
        if url in seen:
            continue
        seen.add(url)
        if count >= MAX_URL_EVIDENCE:
            b.add(
                EvidenceCategory.URL,
                "URL extraction truncated",
                f"{len(urls) - count} further URLs omitted (cap {MAX_URL_EVIDENCE})",
                "derived:cap",
            )
            break
        b.add(EvidenceCategory.URL, "URL in body", url, source)
        count += 1
        # Anchor text showing a different domain than the real target is a
        # deterministic observation, not a judgment.
        anchor_domain = _domain_of_url(anchor) or (
            _domain_of_address(anchor) if "@" in anchor else ""
        )
        href_domain = _domain_of_url(url)
        if anchor_domain and href_domain and anchor_domain != href_domain:
            b.add(
                EvidenceCategory.URL,
                "Anchor text / target domain mismatch",
                f"link text shows '{anchor_domain}' but points to '{href_domain}' ({url})",
                source,
            )

    domains = sorted({_domain_of_url(u) for u, _, _ in urls if _domain_of_url(u)})
    if domains:
        b.add(
            EvidenceCategory.URL,
            "Unique URL domains in body",
            ", ".join(domains),
            "derived:body_urls",
        )


def _extract_attachments(msg: EmailMessage, b: EvidenceBuilder) -> None:
    for part in msg.walk():
        if part.get_content_disposition() != "attachment":
            continue
        payload = part.get_payload(decode=True) or b""
        b.add(
            EvidenceCategory.ATTACHMENT,
            "Attachment",
            (
                f"filename='{part.get_filename() or '(none)'}' "
                f"content_type={part.get_content_type()} size={len(payload)}B "
                f"sha256={hashlib.sha256(payload).hexdigest()}"
            ),
            "mime:attachment",
        )
