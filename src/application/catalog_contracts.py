"""
Brain-local mirrors of business_systems/catalog/models.py's mutation contracts.

Catalog is reached only over HTTP now (business_systems/catalog/api.py) - Brain must not
import business_systems.catalog directly, so these are deliberately separate classes with
the same field shapes, not a shared import. Pydantic v2's model_dump(mode="json") on the
Brain side serializes Decimal/UUID exactly the way Catalog's own matching models expect to
receive them, so the two stay wire-compatible without sharing code.

Field-for-field mirror of catalog/models.py as of the Catalog HTTP-boundary migration -
keep in sync by hand if Catalog's contract changes, the same way any other cross-service
contract in this codebase already requires (see ShopdeckCemAdapter's request payloads).
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SaveSkuInput(BaseModel):
    sku_internal_id: Optional[UUID] = None
    sku_id: str
    colour: Optional[str] = None
    size: Optional[str] = None
    size_type: Optional[str] = None
    pack_configuration: Optional[str] = None
    mrp: Decimal
    selling_price: Decimal
    cost_price: Decimal
    packaging_length_cm: Decimal
    packaging_breadth_cm: Decimal
    packaging_height_cm: Decimal
    packaging_weight_kg: Decimal
    sku_media_urls: List[str] = Field(default_factory=list)


class SaveProductInput(BaseModel):
    product_internal_id: Optional[UUID] = None
    product_code: str
    name: str
    description: Optional[str] = None
    product_type: Optional[str] = None
    brand: str = "Aaram Homes"
    hsn_code: Optional[str] = None
    gst_percentage: Decimal = Decimal("5.00")
    fabric_type: Optional[str] = None
    care_instructions: Optional[str] = None
    set_composition: Optional[str] = None
    product_media_urls: List[str] = Field(default_factory=list)
    size_chart_url: Optional[str] = None
    video_urls: List[str] = Field(default_factory=list)
    collection_tags: List[str] = Field(default_factory=list)


class SaveProductFamilyPayload(BaseModel):
    operation: str = "SaveProductFamily"
    idempotency_key: Optional[str] = None
    product: SaveProductInput
    skus: List[SaveSkuInput] = Field(default_factory=list)


class TransitionLifecycleStatePayload(BaseModel):
    operation: str = "TransitionLifecycleState"
    idempotency_key: Optional[str] = None
    product_internal_id: UUID
    target_state: str


class ValidationErrorDetail(BaseModel):
    error_code: str
    target_entity: str
    target_field: str
    rejected_value: Any = None
    message: str
    is_retryable: bool = False
    requires_human_review: bool = False


class MutationResponse(BaseModel):
    status: str
    operation: str
    product_internal_id: Optional[UUID] = None
    product_code: Optional[str] = None
    lifecycle_state: Optional[str] = None
    affected_sku_count: int = 0
    sku_internal_ids: List[UUID] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    response_metadata: Optional[Dict[str, Any]] = None
