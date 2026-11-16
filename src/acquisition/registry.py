"""Source policy registry. Unknown or undocumented sources fail closed."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import PolicyDecision

SourceType = Literal["official_api", "authorized_feed", "operator_file", "manual", "user_submitted_url"]
AuthorizationStatus = Literal["permitted", "denied", "unknown"]


class SourceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_type: SourceType
    license: str | None = None
    attribution: str | None = None
    permitted_fields: frozenset[str] = frozenset()
    authorization_evidence: str | None = None
    authorization_status: AuthorizationStatus = "unknown"
    enabled: bool = False
    network_acquisition: bool = False
    requests_per_minute: float | None = Field(default=None, gt=0)
    minimum_interval_seconds: float | None = Field(default=None, ge=0)
    allowed_domains: frozenset[str] = frozenset()


class SourceRegistry:
    def __init__(self, registrations: list[SourceRegistration] | None = None):
        self._sources: dict[str, SourceRegistration] = {}
        for registration in registrations or []:
            self.register(registration)

    def register(self, registration: SourceRegistration) -> None:
        if registration.source_id in self._sources:
            raise ValueError(f"source_id already registered: {registration.source_id}")
        self._sources[registration.source_id] = registration

    def get(self, source_id: str) -> SourceRegistration | None:
        return self._sources.get(source_id)

    def all(self) -> tuple[SourceRegistration, ...]:
        return tuple(self._sources.values())

    def policy_decision(self, source_id: str, *, requires_network: bool | None = None) -> PolicyDecision:
        source = self.get(source_id)
        network = bool(requires_network) if requires_network is not None else bool(
            source and source.network_acquisition)
        if source is None:
            return PolicyDecision(source_id=source_id, allowed=False,
                                  reason="Source is not registered; acquisition is blocked.",
                                  requires_network=network)
        if not source.enabled:
            reason = "Source is disabled; acquisition is blocked."
        elif source.authorization_status != "permitted":
            reason = f"Source authorization is {source.authorization_status}; acquisition is blocked."
        elif not source.authorization_evidence or not source.authorization_evidence.strip():
            reason = "Authorization evidence is undocumented; acquisition is blocked."
        elif network and not source.network_acquisition:
            reason = "This source is not registered for network acquisition."
        else:
            return PolicyDecision(source_id=source_id, allowed=True,
                                  reason="Registered source policy permits this acquisition.",
                                  requires_network=network,
                                  authorization_evidence=source.authorization_evidence)
        return PolicyDecision(source_id=source_id, allowed=False, reason=reason,
                              requires_network=network,
                              authorization_evidence=source.authorization_evidence)


DEFAULT_SOURCE_REGISTRY = SourceRegistry([
    SourceRegistration(
        source_id="open_food_facts", source_type="official_api", license="ODbL-1.0",
        attribution="Open Food Facts", permitted_fields=frozenset({
            "code", "product_name", "brands", "quantity", "categories_tags", "countries_tags",
            "ingredients_text", "labels", "nutriments", "nutrition_data_per", "nutriscore_grade",
            "last_modified_t", "name", "brand", "description", "category", "category_hint",
            "variant", "barcode", "gtin", "ingredients", "ingredients_text", "nutrition",
            "nutrition_basis_text", "serving_size", "serving_size_text", "allergens",
            "allergens_text", "claims", "claims_text", "image_reference", "image_url",
            "price", "mrp", "availability", "currency", "source_url", "extracted_at",
        }), authorization_evidence=("Repository source policy: docs/data_sources.md documents user-submitted "
                                    "product page analysis at runtime only; scripts/fetch_off_india.py and "
                                    "src/database/ingest.py document the OFF integration; respect robots.txt "
                                    "and ODbL-1.0 attribution/share-alike terms"),
        authorization_status="permitted", enabled=True, network_acquisition=True,
        requests_per_minute=60, minimum_interval_seconds=1.0,
        # Subdomain matching also covers country sites such as in.openfoodfacts.org.
        allowed_domains=frozenset({"openfoodfacts.org"}),
    ),
    SourceRegistration(
        source_id="operator_price_file", source_type="operator_file", license=None,
        attribution=None, permitted_fields=frozenset({"product_id", "listing_url", "price", "pack", "observed_at"}),
        authorization_evidence=None, authorization_status="unknown", enabled=False,
        network_acquisition=False,
    ),
    SourceRegistration(
        source_id="complete_product_catalog", source_type="operator_file",
        license="unknown", attribution="User-supplied workbook; original dataset license/source not stated",
        permitted_fields=frozenset({"Product Submission ID", "Product name", "Brand name", "Product category",
                                    "Product variant/flavour", "Pack size", "Barcode number",
                                    "Ingredients (copy from pack)", "Nutritional information (per 100 g/ml)",
                                    "Marketing claims (exact wording)",
                                    "Paste or insert a link to the original photo file. Google Form file uploads are stored in Drive. Front packaging photo",
                                    "Back packaging photo", "Ingredient-label photo", "Nutrition-table photo",
                                    "Barcode photo", "Product source URL",
                                    "Indicative planning range only, not a verified live quote. Replace with app prices for the selected delivery pin code and date. Price range (₹, indicative)",
                                    "Blinkit price (₹)", "Zepto price (₹)", "Swiggy Instamart price (₹)",
                                    "Price checked date", "Photo/source notes"}),
        authorization_evidence="User supplied Complete_Product_Catalog_With_JSON_Photos.xlsx and authorized candidate audit/import in this task",
        authorization_status="permitted", enabled=True, network_acquisition=False,
    ),
    SourceRegistration(
        source_id="bigbasket", source_type="authorized_feed", license=None, attribution=None,
        permitted_fields=frozenset(), authorization_evidence=None, authorization_status="unknown",
        enabled=False, network_acquisition=True,
    ),
])
