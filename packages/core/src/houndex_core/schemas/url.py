"""URL canonicalization. Mirrors the TypeScript ``canonicalizeUrl`` and
``extractDomain`` so source-URL handling — and therefore claim identity — stays
stable across the two implementations.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, quote, urlsplit

_TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
    }
)


def canonicalize_url(url: str) -> str:
    trimmed = url.strip()
    parts = urlsplit(trimmed)
    if not parts.scheme:
        # If there's no scheme, assume https.
        parts = urlsplit(f"https://{trimmed}")

    scheme = parts.scheme.lower()
    host = (parts.netloc or "").lower()
    if scheme == "http" and host.endswith(":80"):
        host = host[:-3]
    elif scheme == "https" and host.endswith(":443"):
        host = host[:-4]

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
    ]
    kept.sort(key=lambda pair: (pair[0], pair[1]))
    query = "&".join(f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in kept)

    base = f"{scheme}://{host}{path}"
    return base if query == "" else f"{base}?{query}"


def extract_domain(url: str) -> str:
    host = urlsplit(url).hostname
    if not host:
        host = urlsplit(f"https://{url.strip()}").hostname
    host = (host or "").lower()
    labels = [label for label in host.split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    return ".".join(labels[-2:])
