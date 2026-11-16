"""Fetch a product page safely and politely.

Safety (server-side request forgery): only http(s); no credentials in the URL;
standard ports only; the host must resolve to public addresses (no loopback,
private, link-local, multicast or reserved ranges); redirects are followed by
hand and every hop is checked again. Reads stop at a size limit, and a
timeout applies to every request.

Politeness: robots.txt is honoured, the user agent identifies the project,
requests to one host are spaced out, and pages are cached in data/cache/ so the
demo does not hit the site again (doc section 14).

Known limit: the address is checked before connecting, so a DNS answer that
changes between the check and the connection (DNS rebinding) is not fully
excluded. Run the API behind an egress firewall in production (docs/architecture.md).
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import threading
import time
import urllib.robotparser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from core.config import ROOT

CACHE_DIR = Path(os.environ.get("FETCH_CACHE_DIR") or ROOT / "data" / "cache")
USER_AGENT = "FoodDecisionIntelligence/0.1 (academic project, MSIT GGSIPU)"
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}
HTML_TYPES = ("text/html", "application/xhtml+xml")
MAX_REDIRECTS = 5


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


TIMEOUT = _env_float("FETCH_TIMEOUT_SECONDS", 15.0)
MAX_BYTES = int(_env_float("FETCH_MAX_BYTES", 3_000_000))
MIN_HOST_INTERVAL = _env_float("FETCH_MIN_HOST_INTERVAL_SECONDS", 1.0)
# Opt-in exceptions for local demos only, e.g. "127.0.0.1:8090" for the bundled demo pages
# (./run.sh demo-pages). Empty by default; never set it on a public deployment.
DEV_ALLOW = {h.strip().lower() for h in os.environ.get("FETCH_DEV_ALLOW_HOSTS", "").split(",") if h.strip()}


class FetchError(Exception):
    """A fetch that did not produce a usable page. ``code`` matches the API error codes."""

    def __init__(self, code: str, message: str, http_status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class FetchBlocked(FetchError):
    def __init__(self, message: str, code: str = "robots_disallowed", http_status: int = 403):
        super().__init__(code, message, http_status)


def public_source_fetch_error(exc: FetchError) -> tuple[str, str, int]:
    """Stable user-facing error classification for policy-controlled URL flows."""
    if exc.code == "robots_disallowed":
        return ("robots_disallowed",
                "This source does not permit automated access to this page. We respect its access restrictions. "
                "You can upload a saved copy of the product page or product screenshots.", 403)
    if exc.code == "source_redirect_blocked":
        return ("unsupported_source",
                "This source is not currently supported for automated product extraction. You can upload a saved "
                "product page or packaging screenshots instead.", 403)
    if exc.code in {"fetch_failed", "timeout", "unsupported_content"}:
        return ("source_fetch_failed",
                "The product page could not be retrieved. Please upload a saved page or product screenshots.", 502)
    return exc.code, exc.message, exc.http_status


def _blocked_ip(ip) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified or not ip.is_global)


def resolve(host: str) -> list[str]:
    try:
        return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})
    except socket.gaierror:
        return []


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _host_allowed(host: str, allowed_hosts: set[str] | frozenset[str] | None) -> bool:
    if allowed_hosts is None:
        return True
    host = host.rstrip(".").lower()
    return any(host == domain.rstrip(".").lower()
               or host.endswith("." + domain.rstrip(".").lower()) for domain in allowed_hosts)


def validate_url(url: str, resolver=resolve) -> str:
    """Return the URL if it is safe to fetch, else raise FetchError (blocked_destination / invalid_url)."""
    try:
        parts = urlparse(url.strip())
        port = parts.port
    except ValueError:
        raise FetchError("invalid_url", "The address is not a valid URL.", 422)
    if not parts.scheme or (parts.scheme.lower() in ALLOWED_SCHEMES and not parts.netloc):
        raise FetchError("invalid_url", "Enter a full product page address starting with https://", 422)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise FetchError("blocked_destination", "Only http and https product pages can be analysed.", 400)
    if not parts.hostname:
        raise FetchError("invalid_url", "The URL has no host name.", 422)
    if DEV_ALLOW and f"{(parts.hostname or '').lower()}:{port or (443 if parts.scheme == 'https' else 80)}" in DEV_ALLOW:
        return url
    if parts.username or parts.password:
        raise FetchError("blocked_destination", "URLs with embedded credentials are not fetched.", 400)
    if port not in ALLOWED_PORTS:
        raise FetchError("blocked_destination", "Only the standard web ports (80 and 443) are allowed.", 400)
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise FetchError("blocked_destination", "Local and internal addresses cannot be fetched.", 400)
    addrs = [host] if _is_ip(host) else resolver(host)
    if not addrs:
        raise FetchError("fetch_failed", f"Could not resolve {host}.", 502)
    for a in addrs:
        if _blocked_ip(ipaddress.ip_address(a.split("%")[0])):
            raise FetchError("blocked_destination",
                             "That address points to a private or local network, so it is not fetched.", 400)
    return url


_last_hit: dict[str, float] = {}
_lock = threading.Lock()


def _space_out(host: str) -> None:
    """Keep at least MIN_HOST_INTERVAL seconds between requests to one host."""
    with _lock:
        now = time.monotonic()
        start = max(now, _last_hit.get(host, 0.0) + MIN_HOST_INTERVAL)
        _last_hit[host] = start
    if start > now:
        time.sleep(start - now)


def safe_get(url: str, client: Optional[httpx.Client] = None, accept_html_only: bool = True,
             resolver=resolve,
             allowed_hosts: set[str] | frozenset[str] | None = None) -> tuple[str, str]:
    """GET with per-hop validation, timeout and size limit. Returns (final_url, text)."""
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False,
                                    headers={"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"})
    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            current_host = urlparse(current).hostname or ""
            if not _host_allowed(current_host, allowed_hosts):
                raise FetchBlocked("The page redirected outside the source's registered host allowlist.",
                                   code="source_redirect_blocked")
            validate_url(current, resolver)
            _space_out(urlparse(current).hostname or "")
            try:
                with client.stream("GET", current) as r:
                    if r.is_redirect:
                        loc = r.headers.get("location")
                        if not loc:
                            raise FetchError("fetch_failed", "Redirect without a destination.")
                        current = urljoin(current, loc)
                        continue
                    if r.status_code >= 400:
                        raise FetchError("fetch_failed", f"The site answered HTTP {r.status_code}.", 502)
                    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                    if accept_html_only and ctype and ctype not in HTML_TYPES:
                        raise FetchError("unsupported_content", f"The page is {ctype}, not HTML.", 415)
                    declared = r.headers.get("content-length", "")
                    if declared.isdigit() and int(declared) > MAX_BYTES:
                        raise FetchError("too_large", "The page is larger than the size limit.", 413)
                    body = bytearray()
                    for chunk in r.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise FetchError("too_large", "The page is larger than the size limit.", 413)
                    return current, bytes(body).decode(r.encoding or "utf-8", errors="replace")
            except httpx.TimeoutException:
                raise FetchError("timeout", "The site took too long to respond.", 504)
            except httpx.HTTPError as e:
                raise FetchError("fetch_failed", f"Could not fetch the page ({type(e).__name__}).", 502)
        raise FetchError("fetch_failed", "Too many redirects.", 502)
    finally:
        if own:
            client.close()


def _cache_path(url: str, allowed_hosts: set[str] | frozenset[str] | None = None) -> Path:
    policy_key = "" if allowed_hosts is None else "\0allowed:" + ",".join(sorted(
        host.rstrip(".").lower() for host in allowed_hosts))
    return CACHE_DIR / (hashlib.sha256((url + policy_key).encode()).hexdigest()[:24] + ".html")


def allowed_by_robots(url: str, client: Optional[httpx.Client] = None, resolver=resolve,
                      allowed_hosts: set[str] | frozenset[str] | None = None) -> bool:
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        _, text = safe_get(robots_url, client, accept_html_only=False, resolver=resolver,
                           allowed_hosts=allowed_hosts)
    except FetchError as e:
        if e.code in {"blocked_destination", "source_redirect_blocked"}:
            raise
        return True  # robots.txt missing or unreachable: no stated restriction
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def fetch(url: str, use_cache: bool = True, client: Optional[httpx.Client] = None, resolver=resolve,
          allowed_hosts: set[str] | frozenset[str] | None = None) -> str:
    if allowed_hosts is not None and not _host_allowed(urlparse(url).hostname or "", allowed_hosts):
        raise FetchBlocked("The URL host is outside the source's registered host allowlist.",
                           code="source_redirect_blocked")
    validate_url(url, resolver)
    # A restricted source request must not reuse HTML cached by the older,
    # unrestricted fetch path, where a redirect may have crossed domains.
    path = _cache_path(url, allowed_hosts)
    if use_cache and path.exists():
        return path.read_text(encoding="utf-8")
    if not allowed_by_robots(url, client, resolver, allowed_hosts=allowed_hosts):
        raise FetchBlocked("The site's robots.txt does not allow automated access to this page, so it "
                           "was not fetched.")
    _, text = safe_get(url, client, resolver=resolver, allowed_hosts=allowed_hosts)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def fetch_page(url: str, client: Optional[httpx.Client] = None, resolver=resolve,
               allowed_hosts: set[str] | frozenset[str] | None = None) -> tuple[str, str]:
    """Robots-aware fetch returning the final URL, optionally source-host confined.

    This variant is intended for source-aware acquisition adapters that need
    final-URL provenance. It uses the same destination checks, timeout, size,
    redirect, robots and pacing controls as ``fetch`` and deliberately does
    not read or write the shared HTML cache.
    """
    if allowed_hosts is not None and not _host_allowed(urlparse(url).hostname or "", allowed_hosts):
        raise FetchBlocked("The URL host is outside the source's registered host allowlist.",
                           code="source_redirect_blocked")
    validate_url(url, resolver)
    if not allowed_by_robots(url, client, resolver, allowed_hosts=allowed_hosts):
        raise FetchBlocked("The site's robots.txt does not allow automated access to this page, so it "
                           "was not fetched.")
    return safe_get(url, client, resolver=resolver, allowed_hosts=allowed_hosts)
