"""Synthetic-only tests for the native acquisition foundation; no real product facts."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from acquisition import (
    AcquisitionContext, AcquisitionRecord, FieldProvenance, FieldValue, PolicyDecision,
    DEFAULT_SOURCE_REGISTRY, RawSourceRecord, SourceCapabilities, SourceRegistration, SourceRegistry,
    ValidationIssue, run_dry_run,
)
from acquisition.validation import (valid_gtin, valid_http_url,
                                    validate_acquisition_record, validate_batch,
                                    validate_raw_source_record)

NOW = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)


def provenance(field_name="fixture"):
    return FieldProvenance(source_id="synthetic_test", input_locator=f"fixture:{field_name}",
                           extraction_method="synthetic_fixture", collected_at=NOW,
                           raw_value=f"SYNTHETIC {field_name}", evidence_state="declared")


def sourced(value, field_name="fixture", unit=None):
    return FieldValue(value=value, unit=unit, provenance=provenance(field_name))


def raw_record(record_id="row-1"):
    return RawSourceRecord(source_id="synthetic_test", record_id=record_id,
                           payload={"fixture": "SYNTHETIC ONLY", "row": record_id},
                           record_locator=f"synthetic:{record_id}", retrieved_at=NOW,
                           license="synthetic-test-only", attribution="test fixture",
                           adapter_version="test/1")


def acquisition_record(raw, record_id=None, *, name="SYNTHETIC TEST ITEM", price=Decimal("12.50"),
                       quantity=100, listing_url="https://example.test/synthetic-item"):
    return AcquisitionRecord(
        source_id=raw.source_id, record_id=record_id or raw.record_id,
        source_url="https://example.test/synthetic-source", source_license="synthetic-test-only",
        source_attribution="synthetic fixture", collected_at=NOW, adapter_version="test/1",
        product_identity={
            "source_product_id": sourced("fixture-product-1", "source_product_id"),
            "gtin": sourced("0000000000000", "gtin"),
            "name": sourced(name, "name"),
            "brand": sourced("SYNTHETIC BRAND", "brand"),
            "pack_quantity": sourced(quantity, "pack_quantity", "g"),
            "pack_unit": sourced("g", "pack_unit"),
            "multipack_count": FieldValue(),
        },
        listing={"retailer_name": sourced("SYNTHETIC RETAILER", "retailer_name"),
                 "listing_url": sourced(listing_url, "listing_url") if listing_url else FieldValue()},
        observation={"observed_at": NOW, "observed_at_provenance": provenance("observed_at"),
                     "selling_price": sourced(price, "selling_price", "INR"),
                     "currency": "INR", "currency_provenance": provenance("currency"),
                     "mrp": FieldValue(), "location": {"country": "IN"}},
        raw_record_ref={"payload_sha256": raw.payload_sha256,
                        "record_locator": raw.record_locator},
    )


class SyntheticAdapter:
    source_id = "synthetic_test"
    adapter_version = "test/1"
    capabilities = SourceCapabilities(product_identity=True, retailer_listing=True,
                                      price_observation=True, location_scoped=True)

    def __init__(self, count=1):
        self.fetch_called = False
        self.count = count
        self.yielded = 0

    def fetch(self, context):
        self.fetch_called = True
        for i in range(self.count):
            self.yielded += 1
            yield raw_record(f"row-{i}")

    def normalize(self, raw):
        return acquisition_record(raw)

    def check_policy(self, registry):
        registration = registry.get(self.source_id)
        return registry.policy_decision(self.source_id,
                                        requires_network=registration.network_acquisition if registration else True)


def permitted_registry(source_id="synthetic_test", *, auth_status="permitted", evidence="fixture authorization"):
    return SourceRegistry([SourceRegistration(
        source_id=source_id, source_type="operator_file", permitted_fields=frozenset({"fixture"}),
        authorization_evidence=evidence, authorization_status=auth_status,
        enabled=True, network_acquisition=False,
    )])


def test_versioned_models_keep_nulls_and_reject_naive_timestamps():
    ctx = AcquisitionContext(run_id="synthetic-run", started_at=NOW, location_pin=" 110001 ")
    assert ctx.location_pin == "110001" and ctx.dry_run is True
    with pytest.raises(ValidationError):
        AcquisitionContext(started_at=datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        FieldProvenance(source_id="synthetic_test", extraction_method="fixture",
                        collected_at=datetime(2026, 1, 1))

    raw = raw_record()
    assert len(raw.payload_sha256) == 64
    with pytest.raises(ValidationError):
        RawSourceRecord(source_id="synthetic_test", record_id="bad", payload={"fixture": 1},
                        payload_sha256="0" * 64, retrieved_at=NOW, adapter_version="test/1")
    rec = acquisition_record(raw)
    assert rec.schema_version == "acquisition-record/1"
    assert rec.product_identity.gtin.value == "0000000000000"
    assert rec.product_identity.category.value is None
    assert rec.product_identity.category.provenance is None
    assert SourceCapabilities(product_identity=True).product_identity
    assert ValidationIssue(code="example", field_path="name", message="synthetic").severity == "error"
    assert PolicyDecision(source_id="synthetic_test", allowed=False,
                          reason="synthetic deny", requires_network=False).allowed is False


@pytest.mark.parametrize("gtin", ["0000000000000", "00000000000000"])
def test_valid_gtin_examples_are_checksum_valid_only(gtin):
    assert valid_gtin(gtin)


@pytest.mark.parametrize("gtin", ["0000000000001", "123", "00000000000000x"])
def test_invalid_gtin_structure_or_checksum_is_reported(gtin):
    raw = raw_record()
    rec = acquisition_record(raw)
    rec.product_identity.gtin.value = gtin
    issues = validate_acquisition_record(rec)
    assert any(issue.code == "invalid_gtin" for issue in issues)


def test_quantity_price_url_and_provenance_validation():
    raw = raw_record()
    rec = acquisition_record(raw, price=Decimal("0"), quantity=-2, listing_url="javascript:alert(1)")
    rec.product_identity.pack_unit.value = "litres"
    issues = validate_acquisition_record(rec)
    codes = {issue.code for issue in issues}
    assert {"invalid_quantity", "invalid_quantity_unit", "invalid_price", "invalid_source_url"} <= codes
    rec.product_identity.brand.provenance = None
    assert any(issue.code == "missing_provenance" and issue.field_path.endswith("brand")
               for issue in validate_acquisition_record(rec))
    assert valid_http_url("https://example.test/item")
    assert not valid_http_url("https://user:pw@example.test/item")
    assert not valid_http_url("file:///tmp/item")
    unsafe_raw = RawSourceRecord(source_id="synthetic_test", record_id="bad-url", payload={},
                                 source_url="javascript:alert(1)", retrieved_at=NOW, adapter_version="test/1")
    assert validate_raw_source_record(unsafe_raw)[0].code == "invalid_source_url"


def test_naive_observation_timestamp_is_rejected_at_model_boundary():
    raw = raw_record()
    with pytest.raises(ValidationError):
        AcquisitionRecord(source_id=raw.source_id, record_id="bad-time",
                          observation={"observed_at": datetime(2026, 1, 1)},
                          raw_record_ref={"payload_sha256": raw.payload_sha256})


def test_missing_values_stay_null_and_duplicate_observations_are_only_flagged():
    raw_a, raw_b = raw_record("row-a"), raw_record("row-b")
    a = acquisition_record(raw_a, "candidate-a")
    b = acquisition_record(raw_b, "candidate-b")
    a.product_identity.name = FieldValue(value=" ")
    assert a.product_identity.name.value is None
    report = validate_batch([a, b])
    assert any(i.code == "missing_value" for i in report[a.record_id])
    duplicate_issues = [i for issues in report.values() for i in issues
                        if i.code == "duplicate_observation_candidate"]
    assert len(duplicate_issues) == 1
    assert len({a.record_id, b.record_id}) == 2  # validation does not merge candidates


def test_unknown_denied_or_undocumented_sources_block_before_fetch():
    ctx = AcquisitionContext(run_id="policy-run", started_at=NOW)
    for registry in (
        SourceRegistry(),
        permitted_registry(auth_status="denied"),
        permitted_registry(auth_status="unknown"),
        permitted_registry(evidence=None),
        DEFAULT_SOURCE_REGISTRY,
    ):
        adapter = SyntheticAdapter()
        if registry is DEFAULT_SOURCE_REGISTRY:
            adapter.source_id = "bigbasket"
        result = run_dry_run(adapter, ctx, registry)
        assert result.status == "blocked"
        assert not adapter.fetch_called
        assert result.policy.allowed is False


def test_dry_run_fetches_normalizes_and_validates_without_database_writer():
    adapter = SyntheticAdapter(count=2)
    ctx = AcquisitionContext(run_id="dry-run", started_at=NOW, max_records=1)
    result = run_dry_run(adapter, ctx, permitted_registry())
    assert result.status == "completed" and result.dry_run
    assert result.raw_record_count == 1 and len(result.records) == 1
    assert adapter.fetch_called and adapter.yielded == 1
    assert result.records[0].product_identity.name.value == "SYNTHETIC TEST ITEM"
    with pytest.raises(ValueError, match="Only dry-run"):
        run_dry_run(adapter, AcquisitionContext(run_id="write", started_at=NOW, dry_run=False),
                    permitted_registry())
