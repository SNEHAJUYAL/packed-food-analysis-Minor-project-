"""Dry-run source orchestration. This module has no database writer by design."""
from __future__ import annotations

from itertools import islice

from pydantic import BaseModel, Field

from .adapter import ProductSourceAdapter
from .models import (AcquisitionContext, AcquisitionRecord, PolicyDecision,
                     ValidationIssue)
from .registry import DEFAULT_SOURCE_REGISTRY, SourceRegistry
from .validation import validate_batch, validate_raw_source_record


class AcquisitionRunResult(BaseModel):
    run_id: str
    source_id: str
    dry_run: bool = True
    policy: PolicyDecision
    raw_record_count: int = 0
    records: list[AcquisitionRecord] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    status: str = "ok"


def run_dry_run(adapter: ProductSourceAdapter, context: AcquisitionContext,
                 registry: SourceRegistry = DEFAULT_SOURCE_REGISTRY) -> AcquisitionRunResult:
    """Fetch/normalize/validate only after a fail-closed policy check; never persists.

    A context with ``dry_run=False`` is rejected because persistence is deliberately
    outside this foundation task.
    """
    if not context.dry_run:
        raise ValueError("Only dry-run orchestration is implemented; database writes are not available.")
    registration = registry.get(adapter.source_id)
    policy = registry.policy_decision(adapter.source_id,
                                      requires_network=registration.network_acquisition if registration else True)
    result = AcquisitionRunResult(run_id=context.run_id, source_id=adapter.source_id,
                                  policy=policy, status="ok" if policy.allowed else "blocked")
    if not policy.allowed:
        result.issues.append(ValidationIssue(code="source_policy_blocked", field_path="source_id",
                                             message=policy.reason, severity="error"))
        return result
    try:
        adapter_policy = adapter.check_policy(registry)
    except Exception as exc:
        result.policy = PolicyDecision(source_id=adapter.source_id, allowed=False,
                                       reason=f"Adapter policy check failed: {type(exc).__name__}.",
                                       requires_network=policy.requires_network)
        result.status = "blocked"
        result.issues.append(ValidationIssue(code="source_policy_blocked", field_path="source_id",
                                             message=result.policy.reason, severity="error"))
        return result
    if not adapter_policy.allowed:
        result.policy = adapter_policy
        result.status = "blocked"
        result.issues.append(ValidationIssue(code="source_policy_blocked", field_path="source_id",
                                             message=adapter_policy.reason, severity="error"))
        return result

    result.status = "completed"
    try:
        raw_records = adapter.fetch(context)
        if context.max_records is not None:
            raw_records = islice(raw_records, context.max_records)
        for raw in raw_records:
            result.raw_record_count += 1
            result.issues.extend(validate_raw_source_record(raw))
            if raw.source_id != adapter.source_id:
                result.issues.append(ValidationIssue(code="source_id_mismatch", field_path="source_id",
                                                     message="Raw record source_id does not match adapter source_id.",
                                                     record_id=raw.record_id))
                continue
            try:
                record = adapter.normalize(raw)
            except Exception as exc:
                result.issues.append(ValidationIssue(code="adapter_normalization_error",
                                                     field_path="record", message=f"Normalization failed: {type(exc).__name__}.",
                                                     record_id=raw.record_id))
                continue
            if record.source_id != adapter.source_id:
                result.issues.append(ValidationIssue(code="source_id_mismatch", field_path="source_id",
                                                     message="Normalized record source_id does not match adapter source_id.",
                                                     record_id=record.record_id))
                continue
            if record.raw_record_ref.payload_sha256 != raw.payload_sha256:
                result.issues.append(ValidationIssue(code="payload_reference_mismatch",
                                                     field_path="raw_record_ref.payload_sha256",
                                                     message="Normalized record must reference the exact raw source payload.",
                                                     record_id=record.record_id))
                continue
            if record.collected_at is not None and record.collected_at != raw.retrieved_at:
                result.issues.append(ValidationIssue(code="collection_timestamp_mismatch",
                                                     field_path="collected_at",
                                                     message="Canonical record collection time differs from raw retrieval time.",
                                                     severity="warning", record_id=record.record_id))
            result.records.append(record)
    except Exception as exc:
        result.status = "failed"
        result.issues.append(ValidationIssue(code="adapter_fetch_error", field_path="fetch",
                                             message=f"Adapter fetch failed: {type(exc).__name__}.",
                                             severity="error"))
    for record_issues in validate_batch(result.records).values():
        result.issues.extend(record_issues)
    return result
