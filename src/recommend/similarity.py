"""Find comparable products: TF-IDF over name, brand, category and ingredients + kNN
(cosine), as in the doc's stack (section 9)."""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from core.schema import Product


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
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(docs + [product_text(target)])
    nn = NearestNeighbors(n_neighbors=min(k, len(idx)), metric="cosine").fit(X[:-1])
    dist, ind = nn.kneighbors(X[-1])
    return [(idx[j], round(1.0 - d, 4)) for d, j in zip(dist[0], ind[0])]
