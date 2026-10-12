"""SSRF protection, redirects, size limits and robots.txt in the fetcher (no network)."""
import httpx
import pytest

from extract import fetch as F

PUBLIC = lambda host: ["93.184.216.34"]  # noqa: E731  documentation-style public address


@pytest.fixture(autouse=True)
def _fast(monkeypatch, tmp_path):
    monkeypatch.setattr(F, "MIN_HOST_INTERVAL", 0.0)
    monkeypatch.setattr(F, "CACHE_DIR", tmp_path)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/a", "gopher://x.example/", "javascript:alert(1)",
])
def test_rejects_unsupported_schemes(url):
    with pytest.raises(F.FetchError) as e:
        F.validate_url(url, PUBLIC)
    assert e.value.code == "blocked_destination"


@pytest.mark.parametrize("url", [
    "http://localhost/", "http://127.0.0.1/", "http://10.0.0.5/", "http://192.168.1.1/",
    "http://172.16.3.4/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/",
    "http://0.0.0.0/", "http://[::ffff:127.0.0.1]/", "http://printer.local/", "http://100.64.0.1/",
])
def test_rejects_private_and_local_destinations(url):
    with pytest.raises(F.FetchError) as e:
        F.validate_url(url, PUBLIC)
    assert e.value.code == "blocked_destination"


def test_rejects_hostname_resolving_to_private_address():
    with pytest.raises(F.FetchError) as e:
        F.validate_url("https://evil.example/", lambda h: ["10.1.2.3"])
    assert e.value.code == "blocked_destination"


def test_rejects_credentials_and_odd_ports():
    for url in ("https://user:pw@example.com/", "https://example.com:8080/"):
        with pytest.raises(F.FetchError):
            F.validate_url(url, PUBLIC)


def test_unresolvable_host_fails_closed():
    with pytest.raises(F.FetchError) as e:
        F.validate_url("https://no-such-host.example/", lambda h: [])
    assert e.value.code == "fetch_failed"


def test_accepts_public_https():
    assert F.validate_url("https://brand.example/p/1", PUBLIC)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_redirect_to_private_address_is_blocked():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/p", _client(handler), resolver=PUBLIC)
    assert e.value.code == "blocked_destination"


def test_redirect_chain_is_followed_and_validated():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, html="<html>ok</html>")
    final, text = F.safe_get("https://brand.example/old", _client(handler), resolver=PUBLIC)
    assert final == "https://brand.example/new" and "ok" in text


def test_too_many_redirects():
    client = _client(lambda r: httpx.Response(302, headers={"location": "/loop"}))
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/loop", client, resolver=PUBLIC)
    assert "redirects" in e.value.message


def test_size_limit(monkeypatch):
    monkeypatch.setattr(F, "MAX_BYTES", 1000)
    client = _client(lambda r: httpx.Response(200, html="x" * 5000))
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/big", client, resolver=PUBLIC)
    assert e.value.code == "too_large"


def test_non_html_is_rejected():
    client = _client(lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}))
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/a.pdf", client, resolver=PUBLIC)
    assert e.value.code == "unsupported_content"


def test_timeout_maps_to_timeout_code():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/slow", _client(handler), resolver=PUBLIC)
    assert e.value.code == "timeout"


def test_http_error_status():
    with pytest.raises(F.FetchError) as e:
        F.safe_get("https://brand.example/x", _client(lambda r: httpx.Response(404)), resolver=PUBLIC)
    assert e.value.code == "fetch_failed" and "404" in e.value.message


def test_robots_disallow_blocks_fetch():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /p/\n")
        return httpx.Response(200, html="<html>page</html>")
    with pytest.raises(F.FetchBlocked) as e:
        F.fetch("https://brand.example/p/1", use_cache=False, client=_client(handler), resolver=PUBLIC)
    assert e.value.code == "robots_disallowed"


def test_fetch_ok_and_cached():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, html="<html>page</html>")
    client = _client(handler)
    assert "page" in F.fetch("https://brand.example/p/1", client=client, resolver=PUBLIC)
    assert "page" in F.fetch("https://brand.example/p/1", client=client, resolver=PUBLIC)
    assert calls.count("/p/1") == 1


def test_dev_allowlist_is_exact_host_and_port(monkeypatch):
    monkeypatch.setattr(F, "DEV_ALLOW", {"127.0.0.1:8090"})
    assert F.validate_url("http://127.0.0.1:8090/cereal.html", PUBLIC)
    for url in ("http://127.0.0.1:8091/", "http://127.0.0.1/", "http://localhost:8090/"):
        with pytest.raises(F.FetchError):
            F.validate_url(url, PUBLIC)
