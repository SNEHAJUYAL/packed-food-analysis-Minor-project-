"""HTML fallback extraction with BeautifulSoup, used when structured metadata is
missing or incomplete. Heuristics are deliberately simple and testable."""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from extract.jsonld import empty_extracted

# Ordered: more specific labels first ("saturated fat" before "fat").
NUTRIENT_LABELS = [
    ("added_sugars", r"added\s+sugars?"),
    ("total_sugars", r"(?:total\s+|of\s+which\s+)?sugars?"),
    ("saturated_fat", r"saturated(?:\s+fat(?:ty\s+acids)?)?|sfa"),
    ("trans_fat", r"trans(?:\s+fat(?:ty\s+acids)?)?"),
    ("total_fat", r"(?:total\s+)?fat"),
    ("fibre", r"(?:dietary\s+)?fib(?:re|er)"),
    ("protein", r"proteins?"),
    ("carbohydrate", r"(?:total\s+)?carbohydrates?|carbs"),
    ("energy", r"energy|calories"),
    ("sodium", r"sodium"),
    ("salt", r"salt"),
]
_BASIS_RE = re.compile(r"per\s*100\s*(g|gm|grams?|ml)\b", re.IGNORECASE)
_SERVING_RE = re.compile(r"per\s+(?:serving|serve|portion)", re.IGNORECASE)
_INGREDIENTS_RE = re.compile(
    r"ingredients?\s*[:\-]\s*(.+?)(?=\n\s*\n|allergen|nutrition(?:al)?\s+(?:information|facts|value)|"
    r"net\s+(?:wt|weight|qty|quantity)|storage|best before|$)",
    re.IGNORECASE | re.DOTALL,
)
_PACK_RE = re.compile(r"net\s+(?:wt\.?|weight|qty\.?|quantity|content)\s*[:\-]?\s*([\d.,]+\s*(?:kg|g|gm|ml|l|ltr)\b)",
                      re.IGNORECASE)


def nutrient_key(label: str) -> Optional[str]:
    label = re.sub(r"\(.*?\)", "", label).strip().lower()
    label = re.sub(r"[^a-z\s]", " ", label).strip()
    label = re.sub(r"^(?:of\s+which|including|incl)\s+", "", label)
    for key, pattern in NUTRIENT_LABELS:
        if re.fullmatch(pattern, label) or re.match(rf"(?:{pattern})\b", label):
            return key
    return None


def _label_unit(label: str) -> Optional[str]:
    m = re.search(r"\(\s*(kcal|kj|g|mg|mcg)\s*\)", label, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _pick_energy(cell: str) -> str:
    """"1720 kJ / 410 kcal" -> "410 kcal"."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*kcal", cell, re.IGNORECASE)
    return f"{m.group(1)} kcal" if m else cell


def parse_nutrition_table(soup: BeautifulSoup) -> tuple[dict, Optional[str]]:
    best: dict = {}
    basis = None
    for table in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
        rows = [r for r in rows if r]
        if not rows:
            continue
        context = " ".join([table.get_text(" ", strip=True)[:300]] + [
            (table.find_previous(["h2", "h3", "h4", "p", "caption"]) or soup.new_tag("x")).get_text(" ", strip=True)])
        col = 1
        header = rows[0]
        for i, h in enumerate(header):
            if _BASIS_RE.search(h):
                col = i
                break
        found = {}
        for r in rows:
            if len(r) <= col:
                continue
            key = nutrient_key(r[0])
            if key and key not in found and re.search(r"\d", r[col]):
                cell = r[col]
                if key == "energy":
                    cell = _pick_energy(cell)
                unit = _label_unit(r[0])
                if unit and not re.search(r"[a-zA-Z]", cell):
                    cell = f"{cell} {unit}"
                found[key] = cell
        if len(found) > len(best):
            best = found
            hdr = header[col] if len(header) > col else ""
            m = _BASIS_RE.search(hdr) or _BASIS_RE.search(context)
            if m:
                basis = f"100 {'ml' if m.group(1).lower() == 'ml' else 'g'}"
            elif _SERVING_RE.search(hdr) or _SERVING_RE.search(context):
                basis = None  # per serving without a stated serving size: unknown
    return best, basis


def extract_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = empty_extracted("html")
    og_title = soup.find("meta", property="og:title")
    h1 = soup.find("h1")
    out["name"] = (h1.get_text(" ", strip=True) if h1 else None) or (og_title or {}).get("content")
    for prop in ("product:price:amount", "og:price:amount"):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            out["price"] = tag["content"]
            cur = soup.find("meta", property=prop.replace("amount", "currency"))
            out["currency"] = cur.get("content") if cur else None
            break
    if out["price"] is None:
        tag = soup.find(attrs={"itemprop": "price"})
        if tag:
            out["price"] = tag.get("content") or tag.get_text(strip=True)
    desc = soup.find("meta", attrs={"name": "description"})
    out["description"] = desc.get("content") if desc else None
    brand = soup.find(attrs={"itemprop": "brand"})
    out["brand"] = brand.get_text(" ", strip=True) if brand else None

    text = soup.get_text("\n", strip=False)
    m = _INGREDIENTS_RE.search(text)
    if m:
        out["ingredients_text"] = re.sub(r"\s+", " ", m.group(1)).strip(" .")
    m = _PACK_RE.search(text)
    if m:
        out["pack_size_text"] = m.group(1)
    elif out["name"]:
        q = re.search(r"(\d+(?:\.\d+)?\s*(?:kg|g|gm|ml|l)\b)", out["name"], re.IGNORECASE)
        out["pack_size_text"] = q.group(1) if q else None

    out["nutrition"], out["nutrition_basis_text"] = parse_nutrition_table(soup)
    claims = [out["name"], out["description"]]
    claims += [li.get_text(" ", strip=True) for li in soup.find_all("li")][:50]
    out["claims_text"] = [c for c in claims if c]
    return out
