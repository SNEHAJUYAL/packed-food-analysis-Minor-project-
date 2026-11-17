"""Type a product name, get a direct answer: grade, quality, comparison, alternatives and prices.

Works like a search engine that answers instead of listing links:

1. Find the product: the best stored match, else the best Open Food Facts match (imported and scored).
2. Answer from the evidence: the explainable score and grade, what is good and what to watch, where it
   ranks in its category, healthier alternatives and the cheapest recorded price. The wording is
   generated from the stored analysis by fixed templates, so every sentence traces back to a value.
3. Only when the product cannot be found anywhere, and only if an Anthropic API key is configured,
   ask Claude for a general estimate. That answer is labelled AI-generated and unverified, is never
   stored as product data and gets no score or grade.
"""
from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

import catalog
from database import repository as repo
from recommend.alternatives import alternatives

STORED_CUTOFF = 80
ONLINE_CUTOFF = 70
LIGHT_LABEL = {"total_sugars": "sugar", "saturated_fat": "saturated fat", "total_fat": "fat", "sodium": "salt/sodium",
               "fibre": "fibre", "protein": "protein", "energy": "energy"}
HIGHER_BETTER = {"fibre", "protein"}


def _label(name: Optional[str], brand: Optional[str]) -> str:
    name = name or "this product"
    return name if not brand or name.lower().startswith(brand.lower()) else f"{brand} {name}"


def _score(q: str, name: Optional[str], brand: Optional[str]) -> float:
    return fuzz.token_set_ratio(q.lower(), f"{brand or ''} {name or ''}".lower())


def _coverage(q: str, name: Optional[str], brand: Optional[str]) -> float:
    """Share of the typed words (3+ letters) that appear in the product's brand and name."""
    import re
    words = [w for w in re.findall(r"[a-z0-9]+", q.lower().replace("'", "")) if len(w) > 2]
    hay = re.sub(r"[^a-z0-9 ]", "", f"{brand or ''} {name or ''}".lower().replace("'", ""))
    if not words:
        return 0.0
    return sum(1 for w in words if w in hay or (w.endswith("s") and w[:-1] in hay)) / len(words)


def _good(q: str, h: dict, cutoff: float) -> bool:
    return _score(q, h["name"], h["brand"]) >= cutoff and _coverage(q, h["name"], h["brand"]) >= 0.75


def _find(s: Session, q: str) -> tuple[Optional[int], str, list[str]]:
    """(product_id, how it was found, notes)."""
    notes: list[str] = []
    stored = catalog._stored_matches(s, q, 50)
    if not stored:  # token match failed: try fuzzy over all stored products
        stored = [{"product_id": r.id, "name": r.name, "brand": r.brand, "overall": a.overall_score}
                  for r, a in repo.latest_analyses(s)]
    ranked = sorted(stored, key=lambda h: (-_score(q, h["name"], h["brand"]), h.get("price_inr") is None,
                                           h.get("overall") is None,
                                           -fuzz.ratio(q.lower(), f"{h['brand'] or ''} {h['name'] or ''}".lower())))
    good = [h for h in ranked if _good(q, h, STORED_CUTOFF)]
    if good:
        return good[0]["product_id"], "stored", notes
    try:
        online = catalog.search(s, q, include_online=True, limit=10)
        notes += online["notes"]
        hits = sorted(online["online"], key=lambda h: (-_score(q, h["name"], h["brand"]),
                                                        -fuzz.ratio(q.lower(), f"{h['brand'] or ''} {h['name'] or ''}".lower())))
        good = [h for h in hits if _good(q, h, ONLINE_CUTOFF)]
        if good:
            top = good[0]
            if top.get("product_id"):
                return top["product_id"], "stored", notes
            out = catalog.import_off(s, top["barcode"])
            return out["product_id"], "open_food_facts", notes
    except catalog.CatalogError as e:
        notes.append(e.message)
    return None, "not_found", notes


def _category_rank(s: Session, row, res) -> Optional[dict]:
    if not row.category or res.overall_score is None:
        return None
    scores = sorted((a.overall_score for _, a in repo.latest_analyses(s, row.category) if a.overall_score is not None),
                    reverse=True)
    if len(scores) < 3:
        return None
    rank = scores.index(res.overall_score) + 1
    return {"rank": rank, "of": len(scores), "category": row.category.replace("_", " "),
            "better_than_percent": round(100 * (len(scores) - rank) / len(scores))}


def answer_for_product(s: Session, product_id: int, found_via: str = "stored") -> dict:
    row = repo.get_row(s, product_id)
    res = repo.latest_analysis(s, product_id)
    if res is None:
        from services import analyse_row
        analyse_row(s, row)
        res = repo.latest_analysis(s, product_id)
    rep = res.report
    label = _label(row.name, row.brand)
    nut = rep["dimensions"]["nutrition"]
    ing = rep["dimensions"]["ingredients"]
    claims = rep["dimensions"]["claims"]["claims"]
    good, watch = [], []
    per = "100 ml" if nut.get("basis") == "per_100ml" else "100 g"
    for k, light in (nut.get("traffic_lights") or {}).items():
        fact = nut["facts"].get(k) or {}
        if fact.get("value") is None or light not in ("green", "red"):
            continue
        text = f"{LIGHT_LABEL.get(k, k)} ({fact['value']:g} {fact.get('unit') or ''} per {per})"
        higher = k in HIGHER_BETTER
        if light == "green":
            good.append(("High " if higher else "Low ") + text)
        else:
            watch.append(("Low " if higher else "High ") + text)
    for cls, items in (ing.get("groups") or {}).items():
        if cls in ("added_sugar", "oil_palm", "hydrogenated_fat", "artificial_sweetener", "synthetic_colour",
                   "flavour_enhancer", "refined_flour"):
            names = list(dict.fromkeys(i.split(":")[-1].split("[")[0].strip(" ()") for i in items))[:2]
            watch.append(f"Contains {cls.replace('oil_palm', 'palm oil').replace('_', ' ')}"
                         + (f": {', '.join(n[:40] for n in names)}" if names else ""))
        if cls == "whole_grain":
            good.append("Whole grain in the ingredients")
    for c in claims:
        if c["status"] == "potential inconsistency for review":
            watch.append(f"Claim “{c['matched_text']}” does not meet the FSSAI condition")
    overall = rep["overall"]
    grade, score = overall.get("grade"), overall.get("score")
    rank = _category_rank(s, row, res)
    alts = alternatives(s, product_id, "nutrition", 5, store=False, scope="all") or {}
    prices = catalog.price_summary(s, product_id) or {}

    if score is None:
        verdict = (f"{label} cannot be graded yet: its nutrition information is missing or incomplete. "
                   "What is known is shown below.")
    else:
        verdict = f"{label} scores {score}/100, grade {grade}."
        if rank:
            verdict += (f" It ranks {rank['rank']} of {rank['of']} stored {rank['category']} "
                        f"(better than {rank['better_than_percent']}% of them).")
    if alts.get("alternatives"):
        a = alts["alternatives"][0]
        verdict += f" A healthier pick: {_label(a['name'], a['brand'])} (grade {a['grade']})."
    if prices.get("cheapest") and prices.get("retailers"):
        best = prices["retailers"][0]
        verdict += f" Cheapest recorded price: {prices['cheapest']}, ₹{best['latest_price_inr']:g}."

    return {
        "kind": "evidence", "product_id": product_id, "found_via": found_via, "name": label,
        "grade": grade, "score": score, "status": res.status, "verdict": verdict,
        "good": good[:5], "watch": watch[:6], "category_rank": rank,
        "dimensions": {k: rep["dimensions"][k]["score"] for k in ("nutrition", "ingredients", "transparency", "claims", "value")},
        "alternatives": list({_label(a["name"], a["brand"]).lower(): {
            "product_id": a["product_id"], "name": _label(a["name"], a["brand"]), "grade": a["grade"],
            "overall": a["overall"], "reason": a["rationale"]} for a in reversed(alts.get("alternatives") or [])}.values())[::-1],
        "alternatives_message": alts.get("message"),
        "prices": {"cheapest": prices.get("cheapest"), "spread": prices.get("spread"),
                   "retailers": [{"retailer": r["retailer_label"], "price_inr": r["latest_price_inr"],
                                  "price_per_100": r["latest_price_per_100"], "evidence": r["evidence"]}
                                 for r in (prices.get("retailers") or [])[:5]]},
        "is_synthetic": repo.is_synthetic(row),
        "basis": "Generated from the stored, evidence-labelled analysis (no AI model). Every statement comes from "
                 "a value shown in the full report.",
    }


class AiEstimate(BaseModel):
    product: str
    likely_category: Optional[str] = None
    quality_summary: str = Field(description="Two or three sentences on typical nutrition and ingredients")
    watch_out_for: list[str] = Field(default_factory=list)
    healthier_alternatives: list[str] = Field(default_factory=list, description="Packaged products sold in India")
    confidence: str = Field(description="low, medium or high")
    provider: Optional[str] = None
    web_sources: list[dict[str, str]] = Field(default_factory=list)


class GeminiEstimate(BaseModel):
    """Schema sent to Gemini; web citations come from grounding metadata, not model output."""

    product: str
    likely_category: Optional[str] = None
    quality_summary: str
    watch_out_for: list[str] = Field(default_factory=list)
    healthier_alternatives: list[str] = Field(default_factory=list)
    confidence: str


AI_PROMPT = """A shopper in India typed: "{q}". It is probably a packaged food product.
Use Google Search grounding to identify the product and current publicly available information where possible.
Prefer official manufacturer pages, product labels, and reputable food databases. Describe typical nutrition
and ingredient quality, what to watch out for, and up to three healthier packaged alternatives sold in India.
Do not invent exact numbers, a score or a grade. If the evidence is incomplete or conflicting, say so and set
confidence to low or medium."""


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
JSON_HINT = ("Answer with one JSON object only, with keys: product (string), likely_category (string or null), "
             "quality_summary (string), watch_out_for (list of strings), healthier_alternatives (list of strings), "
             "confidence (\"low\", \"medium\" or \"high\").")


def _env(name: str) -> Optional[str]:
    """Environment variable, else the value in the project's .env (so a key added later works without a restart)."""
    if os.environ.get(name):
        return os.environ[name]
    from pathlib import Path
    env = Path(__file__).resolve().parents[1] / ".env"
    try:
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return value or None
    except OSError:
        pass
    return None


def providers() -> list[str]:
    """AI providers configured in .env, in the order they are tried. All are optional."""
    out = []
    from extract import llm_fallback
    if llm_fallback.available():
        out.append("anthropic")
    if _env("GEMINI_API_KEY"):
        out.append("gemini")
    if _env("GROQ_API_KEY"):
        out.append("groq")
    return out


def ai_available() -> bool:
    return bool(providers())


def _parse_json(text: str) -> Optional[dict]:
    import json
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return AiEstimate.model_validate(json.loads(m.group(0))).model_dump()
    except Exception:
        return None


def _anthropic(q: str, client=None) -> Optional[dict]:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    from extract.llm_fallback import MODEL
    response = client.beta.messages.parse(model=MODEL, max_tokens=4000, output_config={"effort": "low"},
                                          messages=[{"role": "user", "content": AI_PROMPT.format(q=q)}],
                                          output_format=AiEstimate)
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    return response.parsed_output.model_dump()


def _groq(q: str, http=None) -> Optional[dict]:
    import httpx
    http = http or httpx.Client(timeout=40)
    r = http.post(GROQ_URL, headers={"Authorization": f"Bearer {_env('GROQ_API_KEY')}"},
                  json={"model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
                        "response_format": {"type": "json_object"}, "temperature": 0.2,
                        "messages": [{"role": "user", "content": AI_PROMPT.format(q=q) + "\n" + JSON_HINT}]})
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])


def _gemini(q: str, client=None) -> Optional[dict]:
    """Generate an optional Google Search-grounded estimate with the official GenAI SDK.

    The result is deliberately kept separate from stored product evidence. Grounding provides useful
    discovery links, but it does not prove the exact variant or replace a package-label extraction.
    """
    from google import genai
    from google.genai import types

    if client is None:
        client = genai.Client(api_key=_env("GEMINI_API_KEY"))
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    response = client.models.generate_content(
        model=model,
        contents=AI_PROMPT.format(q=q) + "\n" + JSON_HINT,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=GeminiEstimate,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, AiEstimate):
        out = parsed.model_dump()
    elif isinstance(parsed, dict):
        out = AiEstimate.model_validate(parsed).model_dump()
    else:
        out = _parse_json(getattr(response, "text", "") or "")
    if not out:
        return None

    sources: list[dict[str, str]] = []
    candidates = getattr(response, "candidates", None) or []
    metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
    for chunk in getattr(metadata, "grounding_chunks", None) or []:
        web = getattr(chunk, "web", None)
        uri, title = getattr(web, "uri", None), getattr(web, "title", None)
        if uri and uri not in {item["url"] for item in sources}:
            sources.append({"title": title or uri, "url": uri})
    out["web_sources"] = sources[:8]
    return out


def ai_estimate(q: str, client=None) -> Optional[dict]:
    """Try each configured provider in turn; the answer records which one wrote it."""
    errors = []
    for name in providers():
        try:
            out = {"anthropic": lambda: _anthropic(q, client), "groq": lambda: _groq(q),
                       "gemini": lambda: _gemini(q, client)}[name]()
        except Exception as exc:  # a provider that fails or is rate limited is skipped
            errors.append(f"{name}: {type(exc).__name__}")
            continue
        if out:
            out["provider"] = name
            return out
    if errors:
        raise RuntimeError("; ".join(errors))
    return None


def ask(s: Session, q: str, client=None) -> dict:
    q = (q or "").strip()
    if len(q) < 2:
        raise catalog.CatalogError(422, "validation_error", "Type a product name, for example “Maggi masala noodles”.")
    pid, how, notes = _find(s, q)
    if pid is not None:
        out = answer_for_product(s, pid, how)
        out["query"], out["notes"] = q, notes
        if out["score"] is None and ai_available():
            # The product is known but cannot be graded (no nutrition): add a clearly separate AI estimate.
            try:
                out["ai_estimate"] = ai_estimate(out["name"] or q, client)
            except Exception as exc:
                notes.append(f"The AI estimate could not be produced ({str(exc)[:80]}).")
        return out
    base = {"query": q, "notes": notes, "product_id": None,
            "next_steps": ["Paste the product page link", "Upload a photo of the ingredient and nutrition panel",
                           "Enter the label details by hand"]}
    estimate = None
    try:
        estimate = ai_estimate(q, client) if (client is not None or ai_available()) else None
    except Exception as exc:  # the AI path is optional; never break the answer
        notes.append(f"The AI estimate could not be produced ({type(exc).__name__}).")
    if estimate:
        return {**base, "kind": "ai_estimate", "estimate": estimate,
                "verdict": estimate["quality_summary"],
                "basis": f"AI-generated by {estimate.get('provider', 'an AI model')} from general knowledge, not from this "
                         "product's label. Unverified, not scored and not stored. Check the pack before relying on it."}
    return {**base, "kind": "not_found",
            "verdict": f"“{q}” was not found among stored products or on Open Food Facts.",
            "basis": ("AI estimates are switched off: no GROQ_API_KEY, GEMINI_API_KEY or ANTHROPIC_API_KEY is set in .env."
                      if not ai_available() else "No AI estimate was returned.")}
