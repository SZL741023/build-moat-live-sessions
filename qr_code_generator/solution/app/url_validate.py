from urllib.parse import urlparse, urlunparse

BLOCKED_DOMAINS = {
    "malware.com",
    "phishing.net",
}


def validate_url(url: str) -> str:
    if len(url) > 2048:
        raise ValueError("URL too long")

    parsed = urlparse(url)
    scheme = parsed.scheme
    netloc = parsed.netloc
    path = parsed.path

    if scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")

    if netloc.lower() in BLOCKED_DOMAINS:
        raise ValueError("Blocked domain")

    scheme = "https"
    return urlunparse((scheme.lower(), netloc.lower(), path.rstrip("/"), "", "", ""))
