from types import SimpleNamespace

import answer


class FakeGeminiModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_gemini_uses_google_search_grounding_and_returns_sources(monkeypatch):
    source = SimpleNamespace(web=SimpleNamespace(uri="https://example.test/maggi", title="Example source"))
    candidate = SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=[source]))
    response = SimpleNamespace(
        parsed=answer.AiEstimate(
            product="Maggi noodles",
            quality_summary="Check the label for sodium and saturated fat.",
            confidence="medium",
        ),
        candidates=[candidate],
    )
    models = FakeGeminiModels(response)
    client = SimpleNamespace(models=models)
    out = answer._gemini("Maggi noodles", client=client)

    assert out["provider"] is None
    assert out["web_sources"] == [{"title": "Example source", "url": "https://example.test/maggi"}]
    config = models.calls[0]["config"]
    assert config.tools and config.tools[0].google_search is not None
    assert models.calls[0]["model"] == "gemini-3.8-flash"


def test_gemini_is_preferred_when_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("FDI_LLM_ENABLED", raising=False)

    assert answer.providers()[0] == "gemini"
