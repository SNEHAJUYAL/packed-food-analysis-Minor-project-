"""Find comparable products: TF-IDF over name, brand, category and ingredients + kNN
(cosine), as in the doc's stack (section 9)."""
from __future__ import annotations

import math
import re
from collections import Counter

from core.schema import Product

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
except ImportError:  # the Vercel API bundle leaves scikit-learn out to stay under the size limit
    TfidfVectorizer = None


def product_text(p: Product) -> str:
    return " ".join(str(x) for x in (p.name.value, p.brand.value, p.category.value,
                                     p.ingredients_raw.value) if x)


def similar(target: Product, pool: list[Product], k: int = 5, same_category: bool = True) -> list[tuple[int, float]]:
    """Indices into ``pool`` of the k most similar products, with cosine similarity."""
    idx = [i for i, p in enumerate(pool)
           if not same_category or p.category.value == target.category.value]
    if not idx:
        return []
    docs = [product_text(pool[i]) for i in idx]
    if TfidfVectorizer is None:
        return _similar_plain(docs, product_text(target), idx, k)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(docs + [product_text(target)])
    nn = NearestNeighbors(n_neighbors=min(k, len(idx)), metric="cosine").fit(X[:-1])
    dist, ind = nn.kneighbors(X[-1])
    return [(idx[j], round(1.0 - d, 4)) for d, j in zip(dist[0], ind[0])]


_TOKEN = re.compile(r"(?u)\b\w\w+\b")


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    """The same vectors as TfidfVectorizer(ngram_range=(1, 2)) with its defaults (smooth idf, l2 norm)."""
    counts = []
    for t in texts:
        words = _TOKEN.findall(t.lower())
        counts.append(Counter(words + [f"{a} {b}" for a, b in zip(words, words[1:])]))
    n = len(texts)
    df = Counter(term for c in counts for term in c)
    idf = {term: math.log((1 + n) / (1 + d)) + 1 for term, d in df.items()}
    vectors = []
    for c in counts:
        v = {term: tf * idf[term] for term, tf in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vectors.append({term: x / norm for term, x in v.items()})
    return vectors


def _similar_plain(docs: list[str], target_text: str, idx: list[int], k: int) -> list[tuple[int, float]]:
    *pool_vecs, target_vec = _tfidf_vectors(docs + [target_text])
    sims = [sum(x * target_vec.get(term, 0.0) for term, x in v.items()) for v in pool_vecs]
    order = sorted(range(len(sims)), key=lambda j: (-sims[j], j))[:min(k, len(idx))]
    return [(idx[j], round(sims[j], 4)) for j in order]
