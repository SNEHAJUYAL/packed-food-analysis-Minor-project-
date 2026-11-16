"""Protocol for source adapters. Implementations must not write to the database."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from .models import AcquisitionContext, AcquisitionRecord, PolicyDecision, RawSourceRecord, SourceCapabilities
from .registry import SourceRegistry


class ProductSourceAdapter(Protocol):
    source_id: str
    adapter_version: str
    capabilities: SourceCapabilities

    def check_policy(self, registry: SourceRegistry) -> PolicyDecision:
        """Apply any adapter-specific restrictions in addition to the central gate."""
        ...

    def fetch(self, context: AcquisitionContext) -> Iterator[RawSourceRecord]:
        """Read from the registered source; the orchestrator checks policy first."""
        ...

    def normalize(self, record: RawSourceRecord) -> AcquisitionRecord:
        """Map a raw record into the shared versioned acquisition envelope."""
        ...
