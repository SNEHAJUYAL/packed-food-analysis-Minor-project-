"""Fetch a product page politely: robots.txt check, identifying user agent, local cache.

The cache (data/cache/) lets the demo run without hitting the site again (doc section 14).
"""
from __future__ import annotations

import hashlib
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import httpx

from core.config import ROOT

CACHE_DIR = ROOT / "data" / "cache"
USER_AGENT = "FoodDecisionIntelligence/0.1 (academic project, MSIT GGSIPU)"


class FetchBlocked(Exception):
    pass


def _cache_path(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")


def allowed_by_robots(url: str, timeout: float = 10.0) -> bool:
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        r = httpx.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError:
        return True  # robots.txt unreachable: no stated restriction
    if r.status_code >= 400:
        return True
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def fetch(url: str, use_cache: bool = True, timeout: float = 20.0) -> str:
    path = _cache_path(url)
    if use_cache and path.exists():
        return path.read_text(encoding="utf-8")
    if not allowed_by_robots(url):
        raise FetchBlocked(f"robots.txt disallows fetching {url}")
    r = httpx.get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"},
                  timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    return r.text
