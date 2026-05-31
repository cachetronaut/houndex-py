"""Content-addressed identity for claims.

A claim's identity derives from the evidence that produced it: the first 16 hex
chars of SHA-256 over a NUL-joined tuple of (tenant_id, subject_lower,
normalized_claim_text, normalized_source_url). The tenant prefix keeps
collisions structurally isolated to one tenant.

This mirrors the TypeScript ``computeClaimId`` byte-for-byte; the shared parity
fixture enforces that.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .hash import sha256_hex

ClaimId = str

_DIGEST_LEN = 16
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_claim_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def _normalize_source_url(url: str) -> str:
    """Only the authority (host) and path participate; scheme, query, and
    fragment are discarded, and a trailing slash on a non-root path is stripped.
    The whole result is lowercased."""
    parts = urlsplit(url.strip())
    netloc = parts.netloc.lower()
    path = parts.path
    if path == "":
        path = "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return f"{netloc}{path}".lower()


def compute_claim_id(*, tenant_id: str, subject: str, claim_text: str, source_url: str) -> ClaimId:
    payload = "\0".join(
        [
            tenant_id,
            subject.strip().lower(),
            _normalize_claim_text(claim_text),
            _normalize_source_url(source_url),
        ]
    )
    return sha256_hex(payload)[:_DIGEST_LEN]
