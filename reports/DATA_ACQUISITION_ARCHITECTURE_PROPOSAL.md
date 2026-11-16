# Native acquisition architecture proposal

## Design goals

Create one acquisition contract for permitted sources, preserve raw evidence, separate a product variant from retailer listings and time-sensitive observations, and reuse the existing extraction and normalization code. Collection, normalization, validation, matching, and persistence should be separate sateps. An adapter must never write directly to PostgreSQL.

## Proposed flow

```text
Authorized source / operator supplied file
        ↓
Source adapter → RawSourceRecord (immutable payload + source/run metadata)
        ↓
Normalizer → ProductIdentityCandidate + RetailerListingCandidate + ObservationCandidate
        ↓
Validators → accepted records + field issues + quarantine/review queue
        ↓
Identity resolver → exact match / new candidate / ambiguous (human review)
        ↓
Repository writer → product + source provenance + price observation
```

### Components

1. **Source registry and policy:** source key, source kind, interface type (`official_api`, `authorized_feed`, `operator_file`, `user_submitted_url`), permitted fields, license/terms reference, attribution requirements, rate/retention settings, enabled flag, and authorization evidence reference. BigBasket automated product/price collection must be disabled until written authorization or an expressly permitted data interface is recorded.
2. **Adapter:** retrieves permitted data or parses an operator-provided file. It returns raw records and no SQLAlchemy objects. Existing URL fetch, JSON-LD, HTML extraction, and OFF parsing are wrapped/reused rather than rewritten.
3. **Normalization:** maps source-specific fields into the shared canonical record and uses `normalise.units` and `normalise.build` where applicable. Raw cells/text are retained next to normalized values.
4. **Validation and quarantine:** validates identity, units, prices, URLs, GTIN structure/check digit, duplicate keys, timestamp/time zone, and variant compatibility. Valid checksum is only a formatting check, not evidence that a GTIN belongs to a product. Warnings and errors are field-scoped; errors stop persistence and ambiguous matches require review.
5. **Identity resolver:** prioritizes verified GTIN plus pack identity, then exact normalized manufacturer/brand/product/variant/quantity evidence; name similarity alone never merges records. Keep alias/candidate links and resolution evidence. Do not turn retailer title similarity into a product identity assertion without review.
6. **Persistence writer:** maps accepted identity to a stable product row, stores one source record for identity/listing provenance, and appends each timestamped observation. Current database limits are described in `DATABASE_COMPATIBILITY_ASSESSMENT.md`.
7. **Run report:** source, run ID, start/end times, input hash or cursor, adapter version, records fetched/accepted/rejected/ambiguous, duplicate counts, and errors. For a file input, record file hash, sheet/row coordinates, and source license/attribution state.

## Canonical output envelope

Use a versioned JSON/Pydantic model independent of database models. Each reported field should have a value, normalized value if different, unit where relevant, and provenance object. Missing values stay null with an explicit missing reason; they are never represented as zero or fabricated.

```json
{
  "schema_version": "acquisition-record/1",
  "source": {"source_id": "off", "source_kind": "official_api", "source_url": null,
              "license": "ODbL-1.0", "attribution": "Open Food Facts", "authorization_ref": null},
  "run": {"run_id": "...", "adapter_version": "...", "collected_at": "...Z"},
  "product_identity": {
    "source_product_id": {"value": "...", "provenance": {}},
    "gtin": {"value": null, "provenance": {}},
    "name": {"value": "...", "provenance": {}},
    "brand": {"value": null, "provenance": {}},
    "category": {"value": null, "provenance": {}},
    "variant": {"value": null, "provenance": {}},
    "pack": {"quantity": null, "unit": null, "multipack_count": null, "provenance": {}}
  },
  "listing": {"retailer_id": null, "retailer_name": null, "listing_id": null,
              "listing_url": null, "listing_name": null, "image_refs": []},
  "observation": {"observed_at": null, "selling_price": null, "currency": "INR", "mrp": null,
                  "discount_percent": null, "availability": null, "location": {"country": "IN", "pin_code": null}},
  "field_provenance": {},
  "raw_record_ref": {"payload_hash": "...", "record_locator": "..."},
  "validation": {"status": "candidate", "issues": []}
}
```

`provenance` should minimally include source ID, source URL or input locator, extraction method, collected timestamp, source/license metadata, raw value, and a verification/evidence state. Keep listing and observation timestamps distinct: a product page capture can be new while the quoted price or availability was not actually observed at that time.

## Adapter protocol

The Python protocol and detailed requirements are in `docs/SOURCE_ADAPTER_INTERFACE_SPEC.md`. Adapters expose metadata/capability declarations and an iterator of raw records. The runner supplies a bounded client/context with timeouts and policy controls. Adapters do not perform identity merges or database writes.

## Safety and source policy

- Network adapters must call the existing safe fetch client or a source-specific official client with equivalent URL, timeout, response-size, redirect, and host controls.
- Respect authorization, official API limits, terms, robots policy where relevant, and source attribution/license obligations. Do not evade authentication, CAPTCHA, anti-bot controls, location gates, or access restrictions.
- Do not auto-follow a retailer listing behind a blocker through alternate endpoints. Stop and return a policy/access issue.
- Disable adapters by default until the source registry contains a permitted basis and the operator enables it.
- Keep secrets out of source records and logs. Use environment-backed credentials only for an authorized API.
- Preserve raw-source payloads only to the extent permitted by the applicable license/terms; otherwise preserve a content hash, field-level extracts, and locator.

## Rollout sequence

1. Add shared models/protocol, source registry metadata, validators, and synthetic tests. No retailer network adapter.
2. Wrap the existing OFF API flow as an adapter without changing its current ingest behavior. Test canonical output parity against existing OFF normalization.
3. Add an operator-file adapter for manually collected, evidence-backed price observations, extending `database.prices` validation instead of duplicating it. Require source URL/evidence reference, exact product/pack confirmation, observed timestamp and optional PIN.
4. Only after documented permission, add one source-specific official feed/API adapter. Use a feature flag and dry-run mode first.
5. Decide on a listing/observation schema migration only when the proposed fields cannot be safely represented through existing models. That is separate implementation approval.

No adapter, migration, or behavior change is implemented as part of this proposal.
