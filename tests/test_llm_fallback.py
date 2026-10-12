"""LLM fallback, with a fake client (no network, no API key needed)."""
from pathlib import Path
from types import SimpleNamespace

from extract.llm_fallback import LlmProduct, extract_llm, grounded
from normalise.build import build_product

PAGE = (Path(__file__).parent / "fixtures" / "beverage_unstructured.html").read_text(encoding="utf-8")


class FakeMessages:
    def __init__(self, result, stop_reason="end_turn"):
        self.result, self.stop_reason, self.calls = result, stop_reason, []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=self.result)


def fake_client(result, stop_reason="end_turn"):
    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages(result, stop_reason)))


def test_grounding_drops_invented_values():
    text = "Each 100 ml gives you 60 kcal, 14.5 g sugar"
    assert grounded("14.5 g", text) and grounded("60 kcal", text)
    assert not grounded("3.2 g", text)


def test_llm_values_are_grounded_and_built():
    result = LlmProduct(
        name="Demo Mango Drink", brand="Demo Beverages", price="Rs 40", pack_size="250 ml",
        ingredients="mango pulp, water and sugar, plus acidity regulator (INS 330)",
        nutrition_basis="100 ml",
        nutrition={"energy": "60 kcal", "total_sugars": "14.5 g", "total_fat": "0 g", "protein": "0.1 g",
                   "sodium": "35 mg"},  # sodium is not on the page: must be dropped
        claims=["100% Natural taste!", "Rich in vitamin C"],  # second claim is invented
    )
    client = fake_client(result)
    ex = extract_llm(PAGE, "https://example.test/drink", client=client)
    assert "sodium" not in ex["nutrition"]
    assert ex["claims_text"] == ["100% Natural taste!"]
    call = client.beta.messages.calls[0]
    assert call["output_format"] is LlmProduct and "Demo Mango Drink" in call["messages"][0]["content"]
    p = build_product([ex], "https://example.test/drink", "beverages")
    assert p.nutrition_basis == "per_100ml"
    assert p.nutrition["total_sugars"].value == 14.5 and p.nutrition["total_sugars"].source == "llm"
    assert p.nutrition["sodium"].value is None
    assert p.price_inr.value == 40 and p.pack_size.value == 250


def test_refusal_returns_none():
    assert extract_llm(PAGE, "u", client=fake_client(LlmProduct(), "refusal")) is None


def test_not_configured_returns_none(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "FDI_LLM_ENABLED"):
        monkeypatch.delenv(k, raising=False)
    assert extract_llm(PAGE, "u") is None
