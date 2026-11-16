"""Small, dependency-free validation for remote product image references.

The application does not download image bodies. HTTPS-only URLs are passed to
the browser's image decoder, which rejects invalid/non-image responses and
triggers the UI fallback on errors.
"""
import ipaddress
from urllib.parse import urljoin, urlparse

import httpx

IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/x-png", "image/webp",
                    "image/avif", "image/gif", "image/bmp"}


def image_url_from_metadata(value: str, page_url: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        candidate = urljoin(page_url, value.strip())
        parsed = urlparse(candidate)
        if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass  # public DNS names are expected for retailer/CDN images
        if any(ord(char) < 32 for char in candidate):
            return None
        return candidate
    except (TypeError, ValueError):
        return None


def probe_image_content_type(url: str, timeout: float = 3.0) -> bool:
    """Check availability and MIME using HEAD only; never download the image body."""
    from extract.fetch import MAX_REDIRECTS, FetchError, _space_out, validate_url

    current = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            validate_url(current)
            _space_out(urlparse(current).hostname or "")
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                response = client.head(current)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    return False
                current = urljoin(current, location)
                if not image_url_from_metadata(current, current):
                    return False
                continue
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            return response.status_code == 200 and content_type in IMAGE_MIME_TYPES
    except (FetchError, httpx.HTTPError, ValueError, OSError):
        return False
    return False
