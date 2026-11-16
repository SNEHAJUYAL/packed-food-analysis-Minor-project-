"""Native, source-neutral product data acquisition foundation."""

from .adapter import ProductSourceAdapter
from .models import (
    AcquisitionContext,
    AcquisitionRecord,
    FieldProvenance,
    FieldValue,
    ImageReference,
    PolicyDecision,
    RawSourceRecord,
    SourceCapabilities,
    ValidationIssue,
)
from .orchestration import AcquisitionRunResult, run_dry_run
from .registry import DEFAULT_SOURCE_REGISTRY, SourceRegistration, SourceRegistry

__all__ = [
    "AcquisitionContext", "AcquisitionRecord", "AcquisitionRunResult",
    "DEFAULT_SOURCE_REGISTRY", "FieldProvenance", "FieldValue", "ImageReference", "PolicyDecision",
    "ProductSourceAdapter", "RawSourceRecord", "SourceCapabilities", "SourceRegistration",
    "SourceRegistry", "ValidationIssue", "run_dry_run",
]
