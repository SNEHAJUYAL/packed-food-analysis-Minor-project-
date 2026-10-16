"""Evaluation metrics (spec: evaluation framework). Pure functions, unit-tested in tests/test_evaluation.py."""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional, Sequence

NUMERIC_TOLERANCE = 0.02  # values within 2 % count as matching (doc section 10)


def values_match(gold: Any, pred: Any, tol: float = NUMERIC_TOLERANCE) -> bool:
    if gold is None or pred is None:
        return gold is None and pred is None
    if isinstance(gold, (int, float)) and isinstance(pred, (int, float)):
        if gold == pred:
            return True
        return abs(gold - pred) <= tol * max(abs(gold), abs(pred), 1e-9)
    return " ".join(str(gold).lower().split()) == " ".join(str(pred).lower().split())


def field_scores(pairs: Iterable[tuple[Any, Any]]) -> dict:
    """Extraction scoring over (gold, predicted) field pairs.

    TP: both present and matching. FP: predicted but wrong, or predicted where gold is absent.
    FN: gold present but predicted missing or wrong. Exact match counts absent==absent as correct.
    """
    tp = fp = fn = exact = n = 0
    for gold, pred in pairs:
        n += 1
        ok = values_match(gold, pred)
        exact += ok
        if gold is not None and pred is not None:
            if ok:
                tp += 1
            else:
                fp += 1
                fn += 1
        elif pred is not None:
            fp += 1
        elif gold is not None:
            fn += 1
    return {"n_fields": n, "tp": tp, "fp": fp, "fn": fn, "precision": _div(tp, tp + fp),
            "recall": _div(tp, tp + fn), "exact_match_accuracy": _div(exact, n)}


def prf(tp: int, fp: int, fn: int) -> dict:
    p, r = _div(tp, tp + fp), _div(tp, tp + fn)
    f1 = None if p is None or r is None or (p + r) == 0 else 2 * p * r / (p + r)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def label_prf(gold: Sequence[str], pred: Sequence[str], negative: str) -> dict:
    """Micro precision/recall/F1 over items, treating ``negative`` (e.g. 'uncertain') as no label."""
    tp = fp = fn = 0
    for g, p in zip(gold, pred):
        if p != negative and p == g:
            tp += 1
        else:
            if p != negative:
                fp += 1
            if g != negative:
                fn += 1
    return prf(tp, fp, fn)


def binary_rates(gold: Sequence[bool], pred: Sequence[bool]) -> dict:
    tp = sum(g and p for g, p in zip(gold, pred))
    fp = sum((not g) and p for g, p in zip(gold, pred))
    fn = sum(g and (not p) for g, p in zip(gold, pred))
    tn = sum((not g) and (not p) for g, p in zip(gold, pred))
    out = prf(tp, fp, fn)
    out.update({"tn": tn, "false_positive_rate": _div(fp, fp + tn)})
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Spearman rank correlation with average ranks for ties."""
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    vy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return None if vx == 0 or vy == 0 else cov / (vx * vy)


def kendall_tau_b(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    """Kendall's tau-b, which corrects for ties (Nutri-Score has only five grades, so ties are common)."""
    n = len(x)
    if n != len(y) or n < 3:
        return None
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                conc += 1
            else:
                disc += 1
    denom = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    return None if denom == 0 else (conc - disc) / denom


def precision_at_k(ranked: Sequence[Any], relevant: set, k: int = 3) -> Optional[float]:
    top = list(ranked)[:k]
    return _div(sum(1 for x in top if x in relevant), len(top)) if top else None


def ndcg_at_k(ranked: Sequence[Any], gains: dict, k: int = 5) -> Optional[float]:
    """NDCG@k with graded relevance ``gains`` {item: gain}; items without a gain count as 0."""
    dcg = sum(gains.get(x, 0) / math.log2(i + 2) for i, x in enumerate(list(ranked)[:k]))
    ideal = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return None if idcg == 0 else dcg / idcg


def _ranks(v: Sequence[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def _div(a: float, b: float) -> Optional[float]:
    return None if b == 0 else a / b
