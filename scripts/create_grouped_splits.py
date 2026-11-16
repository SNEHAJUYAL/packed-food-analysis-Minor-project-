#!/usr/bin/env python3
"""Create deterministic family-grouped or brand-held-out split manifests (no row-level split)."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:  # package import in tests, direct script import when invoked from the CLI
    from .validate_annotation_dataset import normalized_text, validate_file
except ImportError:  # pragma: no cover - exercised by direct CLI invocation
    from validate_annotation_dataset import normalized_text, validate_file

PARTITIONS = ("train", "validation", "test")


class SplitError(ValueError):
    pass


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: int, b: int):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def read_jsonl(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    records = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SplitError(f"line {line_no}: invalid JSON: {exc}") from exc
        if not isinstance(rec, dict):
            raise SplitError(f"line {line_no}: record must be an object")
        records.append(rec)
    return records, hashlib.sha256(raw).hexdigest()


def path_value(record: dict, *path: str):
    cur: Any = record
    for part in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def eligible_records(records: list[dict], include_synthetic: bool) -> tuple[list[dict], list[dict]]:
    eligible, excluded = [], []
    seen = set()
    for rec in records:
        kind = rec.get("record_type")
        if kind == "template":
            excluded.append({"record_id": rec.get("record_id"), "reason": "template"})
            continue
        if kind == "synthetic_fixture" and not include_synthetic:
            excluded.append({"record_id": rec.get("record_id"), "reason": "synthetic_fixture"})
            continue
        if kind not in ({"annotation", "synthetic_fixture"} if include_synthetic else {"annotation"}):
            excluded.append({"record_id": rec.get("record_id"), "reason": "unsupported_record_type"})
            continue
        rid = rec.get("record_id")
        if not isinstance(rid, str) or not rid.strip():
            raise SplitError("Every split-eligible record needs a nonempty stable record_id")
        if rid in seen:
            raise SplitError(f"Duplicate record_id {rid!r}")
        seen.add(rid)
        if kind == "annotation" and path_value(rec, "verification", "status") != "verified":
            excluded.append({"record_id": rid, "reason": "not_record_verified"})
            continue
        required_ids = {
            "brand_id": path_value(rec, "identity", "brand", "brand_id"),
            "family_id": path_value(rec, "identity", "family", "family_id"),
            "variant_id": path_value(rec, "identity", "variant", "variant_id"),
        }
        missing = [name for name, value in required_ids.items() if not isinstance(value, str) or not value.strip()]
        if missing:
            excluded.append({"record_id": rid, "reason": "unresolved_group_ids", "missing": missing})
            continue
        eligible.append(rec)
    return eligible, excluded


def group_components(records: list[dict], mode: str) -> tuple[list[list[int]], dict]:
    """Connect records sharing leakage-sensitive IDs/source lineage or likely near-duplicate identity."""
    uf = UnionFind(len(records))
    seen: dict[tuple, int] = {}
    identity_by_index = []
    for i, rec in enumerate(records):
        brand = path_value(rec, "identity", "brand", "brand_id")
        family = path_value(rec, "identity", "family", "family_id")
        variant = path_value(rec, "identity", "variant", "variant_id")
        gtin = path_value(rec, "identity", "pack", "gtin", "value")
        gtin_state = path_value(rec, "identity", "pack", "gtin", "state")
        if gtin_state != "verified":
            gtin = None
        gtin = re.sub(r"[ -]", "", gtin) if isinstance(gtin, str) else None
        keys = [("family", family), ("variant", variant)]
        if gtin:
            keys.append(("gtin", gtin))
        for src in path_value(rec, "evidence", "source_records") or []:
            if isinstance(src, dict) and src.get("source_record_id"):
                keys.append(("source", src["source_record_id"]))
        # Same brand+family+variant name/pack is a candidate group even if IDs were accidentally duplicated.
        name = normalized_text(path_value(rec, "identity", "product_name", "value"))
        vname = normalized_text(path_value(rec, "identity", "variant", "name", "value"))
        quantity = path_value(rec, "identity", "pack", "declared_quantity", "value") or {}
        amount = quantity.get("amount") if isinstance(quantity, dict) else None
        unit = normalized_text(quantity.get("unit")) if isinstance(quantity, dict) else ""
        if brand and (name or vname):
            fingerprint = ("identity", brand, name, vname, str(amount), unit)
            keys.append(fingerprint)
        # In brand-held-out mode, all records under one brand are a single split group.
        if mode == "brand_held_out":
            keys.append(("brand", brand))
        for key in keys:
            if key in seen:
                uf.union(i, seen[key])
            else:
                seen[key] = i
        identity_by_index.append({"brand_id": brand, "family_id": family, "variant_id": variant,
                                  "gtin": gtin, "brand_name": normalized_text(path_value(rec, "identity", "brand", "name", "value")),
                                  "name": name or vname})

    # Conservative close-duplicate guard within a brand. Candidates are kept together; no records are merged.
    for i, left in enumerate(identity_by_index):
        for j in range(i + 1, len(identity_by_index)):
            right = identity_by_index[j]
            if left["brand_id"] != right["brand_id"]:
                continue
            if left["name"] and right["name"] and SequenceMatcher(None, left["name"], right["name"]).ratio() >= 0.94:
                uf.union(i, j)

    groups = defaultdict(list)
    for i in range(len(records)):
        groups[uf.find(i)].append(i)
    components = list(groups.values())
    # In brand-held-out mode, inconsistent brand IDs connected by a family must stay together;
    # this is conservative and the leakage audit below confirms no brand crosses partitions.
    details = {"leakage_component_count": len(components), "group_sizes": [len(g) for g in components],
               "close_duplicate_rule": "same brand and normalized product/variant name similarity >= 0.94",
               "components": [[records[i].get("record_id") for i in group] for group in components]}
    return components, details


def assign_components(components: list[list[int]], seed: int, ratios: dict[str, float]) -> dict[int, str]:
    if len(components) < 3:
        raise SplitError(f"Need at least 3 independent leakage groups to populate train/validation/test; got {len(components)}")
    rng = random.Random(seed)
    order = list(range(len(components)))
    rng.shuffle(order)
    # Largest groups first reduces imbalance; seeded order breaks equal-size ties reproducibly.
    order.sort(key=lambda i: len(components[i]), reverse=True)
    total = sum(len(x) for x in components)
    targets = {p: ratios[p] * total for p in PARTITIONS}
    counts = {p: 0 for p in PARTITIONS}
    assignment = {}
    for group_idx in order:
        size = len(components[group_idx])
        empty = [p for p in PARTITIONS if counts[p] == 0]
        candidates = empty if empty else list(PARTITIONS)
        partition = min(candidates, key=lambda p: (abs((counts[p] + size) - targets[p]), counts[p] / max(targets[p], 1)))
        assignment[group_idx] = partition
        counts[partition] += size
    if any(counts[p] == 0 for p in PARTITIONS):
        raise SplitError("Could not populate all partitions with the available independent groups")
    return assignment


def leakage_audit(records: list[dict], by_record: dict[str, str], mode: str) -> dict:
    keys = ["family_id", "variant_id", "gtin", "source_record_id"]
    if mode == "brand_held_out":
        keys.append("brand_id")
    partitions_by_key = defaultdict(set)
    for rec in records:
        split = by_record[rec["record_id"]]
        values = {
            "brand_id": path_value(rec, "identity", "brand", "brand_id"),
            "family_id": path_value(rec, "identity", "family", "family_id"),
            "variant_id": path_value(rec, "identity", "variant", "variant_id"),
        }
        gtin = path_value(rec, "identity", "pack", "gtin", "value")
        if path_value(rec, "identity", "pack", "gtin", "state") == "verified" and isinstance(gtin, str):
            values["gtin"] = re.sub(r"[ -]", "", gtin)
        for src in path_value(rec, "evidence", "source_records") or []:
            if isinstance(src, dict) and src.get("source_record_id"):
                partitions_by_key[("source_record_id", src["source_record_id"])].add(split)
        for key, value in values.items():
            if value:
                partitions_by_key[(key, value)].add(split)
    leaks = [{"key_type": key[0], "key": key[1], "partitions": sorted(parts)}
             for key, parts in partitions_by_key.items()
             if len(parts) > 1 and (key[0] in keys)]
    return {"status": "pass" if not leaks else "fail", "checked_group_keys": keys,
            "leakage_count": len(leaks), "leaks": leaks}


def create_manifest(dataset: Path, seed: int = 20261116, mode: str = "family",
                    train: float = 0.70, validation: float = 0.15, test: float = 0.15,
                    include_synthetic: bool = False) -> dict:
    total_ratio = train + validation + test
    if any(x <= 0 for x in (train, validation, test)) or abs(total_ratio - 1.0) > 1e-8:
        raise SplitError("Train, validation and test proportions must all be > 0 and sum to 1")
    if mode not in {"family", "brand_held_out"}:
        raise SplitError("mode must be family or brand_held_out")
    validation_result = validate_file(dataset, include_examples=include_synthetic)
    if validation_result.get("status") != "ok":
        first = validation_result.get("errors", [])[:5]
        raise SplitError(f"Dataset validation failed with {validation_result.get('errors_count')} errors: {first}")
    records, digest = read_jsonl(dataset)
    eligible, excluded = eligible_records(records, include_synthetic)
    if not eligible:
        raise SplitError("No verified, identity-resolved annotation records are eligible")
    components, details = group_components(eligible, mode)
    group_assignment = assign_components(components, seed, {"train": train, "validation": validation, "test": test})
    by_record = {}
    for group_index, indexes in enumerate(components):
        for i in indexes:
            by_record[eligible[i]["record_id"]] = group_assignment[group_index]
    audit = leakage_audit(eligible, by_record, mode)
    if audit["status"] != "pass":
        raise SplitError(f"Leakage detected: {audit['leaks']}")
    membership = {p: sorted(rid for rid, part in by_record.items() if part == p) for p in PARTITIONS}
    counts = {p: len(membership[p]) for p in PARTITIONS}
    return {
        "manifest_version": "1.0",
        "dataset_path": str(dataset),
        "dataset_sha256": digest,
        "dataset_version": sorted({r.get("dataset_version") for r in eligible}),
        "taxonomy_version": sorted({r.get("taxonomy_version") for r in eligible}),
        "split_mode": mode,
        "group_key": "brand_id + family_id + variant_id + verified GTIN + source lineage + duplicate guard" if mode == "family" else "brand_id + family_id + variant_id + verified GTIN + source lineage + duplicate guard",
        "seed": seed,
        "proportions_requested": {"train": train, "validation": validation, "test": test},
        "record_counts": counts,
        "eligible_records": len(eligible),
        "excluded_records": excluded,
        "grouping": details,
        "record_ids": membership,
        "record_to_partition": dict(sorted(by_record.items())),
        "leakage_audit": audit,
        "synthetic_fixture_mode": bool(include_synthetic),
        "warning": "Group allocation is deterministic and approximate; inspect category/source balance before evaluation. Do not use synthetic fixture manifests as research splits.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Frozen annotation JSONL input; never modified")
    parser.add_argument("--output", type=Path, required=True, help="Manifest output JSON path")
    parser.add_argument("--mode", choices=("family", "brand_held_out"), default="family")
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--validation", type=float, default=0.15)
    parser.add_argument("--test", type=float, default=0.15)
    parser.add_argument("--include-synthetic-fixtures", action="store_true",
                        help="TEST ONLY: permit explicitly tagged synthetic_fixture records for tooling tests")
    args = parser.parse_args(argv)
    try:
        manifest = create_manifest(args.dataset, args.seed, args.mode, args.train, args.validation, args.test,
                                   args.include_synthetic_fixtures)
    except (OSError, SplitError, UnicodeDecodeError) as exc:
        print(f"split generation failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "counts": manifest["record_counts"],
                      "leakage_audit": manifest["leakage_audit"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
