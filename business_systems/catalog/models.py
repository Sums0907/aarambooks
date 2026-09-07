"""
Domain Models and Inbound/Outbound Data Contracts for Catalog BS
Strictly conforms to documents 02-catalog-domain-model.md and 04-catalog-contracts.md.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# 1. CORE CANONICAL DOMAIN ENTITIES
# =============================================================================

class ProductEntity(BaseModel):
    """Canonical Commercial Product Offering Family."""
    internal_id: UUID = Field(default_factory=uuid4)
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
    lifecycle_state: str = "DRAFT"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SKUEntity(BaseModel):
    """Canonical Sellable Commercial Unit."""
    internal_id: UUID = Field(default_factory=uuid4)
    product_internal_id: UUID
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PriceHistoryEntity(BaseModel):
    """Immutable Ledger of SKU Pricing Adjustments."""
    id: Optional[int] = None
    sku_internal_id: UUID
    previous_mrp: Optional[Decimal] = None
    new_mrp: Decimal
    previous_selling_price: Optional[Decimal] = None
    new_selling_price: Decimal
    previous_cost_price: Optional[Decimal] = None
    new_cost_price: Decimal
    changed_by: str = "SYSTEM"
    changed_at: Optional[datetime] = None


class ChannelMappingEntity(BaseModel):
    """External Sales Channel Token Mapping."""
    id: Optional[int] = None
    channel: str = "SHOPDECK"
    sku_internal_id: UUID
    external_sku_token: str
    external_product_token: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PublicationArtifactEntity(BaseModel):
    """Tracked Versioned Publication Artifact."""
    artifact_id: UUID = Field(default_factory=uuid4)
    channel: str = "SHOPDECK"
    artifact_type: str = "CSV_46_COLUMN"
    file_path: str
    content_hash: Optional[str] = None
    exported_sku_count: int
    status: str = "COMMITTED"
    generated_by: str = "SYSTEM"
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    error_message: Optional[str] = None


class IdempotencyRecordEntity(BaseModel):
    """Persisted 24-Hour Mutation Idempotency Record."""
    idempotency_key: str
    operation: str
    request_hash: str
    response_payload: Dict[str, Any]
    created_at: Optional[datetime] = None
    expires_at: datetime


# =============================================================================
# 2. INBOUND MUTATION CONTRACT PAYLOADS
# =============================================================================

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


class RenameProductCodePayload(BaseModel):
    operation: str = "RenameProductCode"
    idempotency_key: Optional[str] = None
    product_internal_id: UUID
    new_product_code: str


class TransitionLifecycleStatePayload(BaseModel):
    operation: str = "TransitionLifecycleState"
    idempotency_key: Optional[str] = None
    product_internal_id: UUID
    target_state: str  # 'DRAFT' or 'READY'


# =============================================================================
# 3. OUTBOUND CONTRACT RESPONSES
# =============================================================================

class ValidationErrorDetail(BaseModel):
    error_code: str
    target_entity: str  # 'PRODUCT' or 'SKU'
    target_field: str
    rejected_value: Any = None
    message: str
    is_retryable: bool = False
    requires_human_review: bool = False


class ValidationReport(BaseModel):
    is_valid: bool
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MutationResponse(BaseModel):
    status: str  # 'SUCCESS', 'REJECTED', 'UNCHANGED_IDEMPOTENT'
    operation: str
    product_internal_id: Optional[UUID] = None
    product_code: Optional[str] = None
    lifecycle_state: Optional[str] = None
    affected_sku_count: int = 0
    sku_internal_ids: List[UUID] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    response_metadata: Optional[Dict[str, Any]] = None
