"""First demo UI (doc section 9: Streamlit is acceptable for the first demo; Next.js later).

Run from the repo root:  streamlit run web/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.schema import CATEGORIES, NUTRIENTS  # noqa: E402
from extract.fetch import FetchBlocked  # noqa: E402
from normalise.build import build_product  # noqa: E402
from pipeline import analyse_html, analyse_url, extract_all  # noqa: E402
from recommend.ranker import compare  # noqa: E402

SAMPLES = {p.stem: p for p in sorted((ROOT / "tests" / "fixtures").glob("*.html"))}
LIGHT = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
STATUS = {"consistent with available evidence": "✅", "requires context": "ℹ️",
          "potential inconsistency for review": "⚠️", "cannot be verified from available information": "❔"}

st.set_page_config(page_title="Food Decision Intelligence", page_icon="🥣", layout="wide")
st.title("Food Decision Intelligence")
st.caption("Understand → Evaluate → Compare → Decide. Prototype: sample pages are synthetic test fixtures, "
           "not real products.")

tab_one, tab_compare = st.tabs(["Analyse a product", "Compare products"])


def show_report(r: dict) -> None:
    p = r["product"]
    o = r["overall"]
    c1, c2, c3 = st.columns([2, 1, 1])
    name, brand = p["name"]["value"] or "Unnamed product", p["brand"]["value"]
    c1.subheader(name if not brand or name.lower().startswith(brand.lower()) else f"{brand} {name}")
    c1.write(f"Category: **{p['category']['value'] or 'unknown'}** ({p['category']['label']})")
    c2.metric("Overall", f"{o['score']}/100" if o["score"] is not None else "unknown")
    c3.metric("Grade", o["grade"] or "–")
    for note in o["notes"]:
        st.info(note)
    if p["conflict_flag"]:
        st.warning("Sources disagree: " + "; ".join(p["conflicts"]))

    st.markdown("#### Dimension scores")
    for name, d in r["dimensions"].items():
        score = d["score"]
        with st.expander(f"{name.capitalize()}: {round(score) if score is not None else 'not scored'}"):
            for line in d["explanation"]:
                st.write("• " + line)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Nutrition (raw facts)")
        n = r["dimensions"]["nutrition"]
        per = "100 ml" if n["basis"] == "per_100ml" else "100 g"
        rows = []
        for k, unit in NUTRIENTS.items():
            f = n["facts"][k]
            rows.append({"nutrient": k, f"per {per}": "–" if f["value"] is None else f"{f['value']:g} {unit}",
                         "light": LIGHT.get(n["traffic_lights"].get(k), ""), "evidence": f["evidence"]})
        st.dataframe(rows, hide_index=True, width="stretch")
    with right:
        st.markdown("#### Claims")
        claims = r["dimensions"]["claims"]["claims"]
        if not claims:
            st.write("No front-of-pack claims found.")
        for c in claims:
            st.write(f"{STATUS[c['status']]} **{c['matched_text']}**: {c['status']}")
            for fact in c["facts"]:
                st.caption(fact)
            st.caption(c["reason"])
        st.markdown("#### Ingredients")
        groups = r["dimensions"]["ingredients"].get("groups", {})
        for g, items in groups.items():
            st.write(f"**{g.replace('_', ' ')}**: {', '.join(items)}")
        if p["allergens"]:
            st.write("**Allergens:** " + ", ".join(p["allergens"]))
        fop = r["fop_warning_simulation"]
        st.markdown("#### Proposed FSSAI front-of-pack warning")
        st.write(f"{fop['status']}: {fop['reason']}")
    st.caption(r["disclaimer"])


with tab_one:
    mode = st.radio("Input", ["Sample page", "Product URL"], horizontal=True)
    category = st.selectbox("Category (optional override)", ["auto"] + CATEGORIES)
    cat = None if category == "auto" else category
    if mode == "Sample page":
        name = st.selectbox("Sample", list(SAMPLES))
        if st.button("Analyse", key="sample"):
            show_report(analyse_html(SAMPLES[name].read_text(encoding="utf-8"), f"sample://{name}", cat))
    else:
        url = st.text_input("Product URL")
        if st.button("Analyse", key="url") and url:
            try:
                show_report(analyse_url(url, cat))
            except FetchBlocked as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Could not fetch or parse the page: {e}")

with tab_compare:
    st.write("Paste product URLs from one category, one per line.")
    urls = st.text_area("URLs")
    cat2 = st.selectbox("Category", CATEGORIES, key="cmp_cat")
    if st.button("Compare") and urls.strip():
        from extract.fetch import fetch
        products = []
        for u in [u.strip() for u in urls.splitlines() if u.strip()]:
            try:
                products.append(build_product(extract_all(fetch(u), u), u, cat2))
            except Exception as e:
                st.error(f"{u}: {e}")
        if len(products) >= 2:
            out = compare(products)
            for k, v in out["picks"].items():
                if v:
                    st.success(f"**{k.replace('_', ' ')}**: {v['reason']}")
            st.dataframe([{k: row[k] for k in ("name", "brand", "overall", "grade", "nutrition", "price_per_100")}
                          for row in out["ranking"]], hide_index=True, width="stretch")
