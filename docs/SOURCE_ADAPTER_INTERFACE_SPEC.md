# Source adapter interface specification

This contract is implemented by `src/acquisition/adapter.py`; it does not add a source-specific collector.

## Python-facing protocol

Adapters should depend on small source-neutral dataclasses/Pydantic types. Do not return ORM rows from adapters.

```python
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class SourceCapabilities:
    product_identity: bool
    retailer_listing: bool
    price_observation: bool
    images: bool
    location_scoped: bool

@dataclass(frozen=True)
class AcquisitionContext:
    run_id: str
    started_at: str                 # RFC 3339 UTC
    location_pin: str | None = None
    dry_run: bool = True
    max_records: int | None = None

class ProductSourceAdapter(Protocol):
    source_id: str
    adapter_version: str
    capabilities: SourceCapabilities

    def check_policy(self, registry: "SourceRegistry") -> "PolicyDecision": ...
    def fetch(self, context: AcquisitionContext) -> Iterator["RawSourceRecord"]: ...
    def normalize(self, record: "RawSourceRecord") -> "AcquisitionRecord": ...
```

The central registry decision is authoritative and runs before adapter policy or `fetch()`. The adapter policy may only apply additional restrictions. `run_dry_run()` owns record limits, validation, duplicate reporting and result status. A source may implement a file reader instead of network `fetch`; it must still conform to the same raw record envelope. There is deliberately no persistence writer in this implementation.

## Required record properties

`RawSourceRecord` should include `source_id`, source record identifier if supplied, input locator (URL/API cursor/file hash + sheet/row), original field map or permitted raw payload, payload SHA-256, retrieval timestamp, license/attribution metadata, and adapter version. Keep source fields unmodified; store normalized output separately.

`AcquisitionRecord` is the canonical envelope in the architecture proposal. For each field, provenance must identify the exact source/locator and method. Identity fields belong to a product identity candidate; retailer-specific title, listing URL, retailer, and image references belong to a listing; price, MRP, discount, availability, PIN code and observed timestamp belong to one observation.

## Failure and validation behavior

Adapters return no fake empty values. If a source field is absent, return null plus an absent reason. If access is unauthorized, blocked, CAPTCHA-protected, or otherwise restricted, return a policy/access failure and stop; do not retry via an alternate route to bypass it. Transient network errors may retry within a bounded policy. Every error has a stable code, safe message, and source/run reference; credentials and page content must not be written to logs.

Validation should emit field-addressed issues with severity, rule ID, and supplied value/provenance reference (sensitive values redacted if needed). Minimum checks:

- HTTP(S) URL parse/scheme/host checks for URLs; no credential-bearing URLs.
- Price parsed to positive decimal INR. Distinguish selling price from MRP; reject MRP below selling price only as a review issue because promotions/data timing may explain it.
- Quantity is positive decimal in canonical `g` or `ml`; multipack count is positive integer; preserve original text and do not equate mass and volume.
- GTIN checksum and length are checked; identity ownership is not inferred from checksum. Duplicate GTINs across conflicting exact variants are quarantined for review.
- Availability maps to a small canonical enum while preserving source value.
- Timestamp is timezone-aware; preserve source timezone and canonicalize storage to UTC.
- Same observation duplicate candidates are detected using source/listing/product, location, timestamp, price, pack and source record identity. Never silently discard conflicting values.
- Candidate matching verifies brand/name/variant/pack compatibility; ambiguous matches do not auto-merge.

## Persistence contract

After validation, the writer receives an explicitly resolved product ID or a create-product decision. It writes product identity and identity evidence separately from listing and observation evidence where the database supports it. If only legacy `ProductRow`/`PriceObservation` can represent a field, the writer records an explicit mapping decision and emits a compatibility warning for fields that would be lossy. The adapter itself never commits a transaction.

## Source policy contract

Each adapter declares `source_id`, source class, terms/license reference, attribution text, permitted uses, authorization evidence reference, network host allowlist if applicable, rate limits, and whether it can access price/location data. Unknown policy means disabled. The BigBasket adapter remains absent/disabled unless written authorization or an expressly permitted data interface has been established and recorded.

The current registry is `DEFAULT_SOURCE_REGISTRY` in `src/acquisition/registry.py`. Open Food Facts is enabled under the repository's existing API/license documentation; the operator price file is disabled until specific provenance/policy is registered; BigBasket is explicitly disabled with unknown authorization. Unregistered sources are blocked.
