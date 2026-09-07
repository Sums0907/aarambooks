from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, PrivateAttr
import uuid


class DecisionStatus(str, Enum):
    PROPOSE_ATTACH = "PROPOSE_ATTACH"
    PROPOSE_NEW = "PROPOSE_NEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"


class AuthorizedContext(BaseModel):
    """
    Authenticated context bridged securely from an upstream boundary (e.g. Brain Core or Catalog BS Read View).
    This is the ONLY way an internal_id is treated as an authorized target.
    """
    authorized_parent_internal_id: Optional[str] = Field(None, description="An explicitly authorized existing Product internal_id to attach to.")
    authoritative_new_product_flag: bool = Field(False, description="An explicitly authorized assertion that this must be a new product.")


class IntakeRequest(BaseModel):
    """
    The raw input boundary for a cognitive session.
    """
    raw_text: str = Field(..., description="Raw unstructured input string. Any UUIDs in here are untrusted.")
    authorized_context: Optional[AuthorizedContext] = Field(default_factory=AuthorizedContext)
    image_uris: List[str] = Field(default_factory=list, description="Passive evidence references.")
    extracted_attributes: Dict[str, Any] = Field(default_factory=dict, description="Attributes extracted prior to resolution.")


class CandidateSKU(BaseModel):
    proposed_sku_id: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class CandidateProduct(BaseModel):
    proposed_product_code: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    candidate_skus: List[CandidateSKU] = Field(default_factory=list)


class ResolutionDecision(BaseModel):
    """
    The final cognitive output from Catalog ID before handing off to Brain Core / Catalog BS.
    """
    status: DecisionStatus
    reasoning: str
    proposed_parent_internal_id: Optional[str] = None
    candidate_product: Optional[CandidateProduct] = None
    
    class Config:
        frozen = True

class FieldProvenance(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"
    IMAGE_INFERRED = "IMAGE_INFERRED"
    SABAQ_REUSED = "SABAQ_REUSED"
    AZM_DERIVED = "AZM_DERIVED"
    BUSINESS_CONFIG = "BUSINESS_CONFIG"
    AI_PROPOSED = "AI_PROPOSED"
    UNKNOWN_REQUIRES_USER = "UNKNOWN_REQUIRES_USER"


class CatalogIntent(str, Enum):
    CREATE_FAMILY = "CREATE_FAMILY"
    UPSERT_SKUS = "UPSERT_SKUS"


class DraftField(BaseModel):
    value: Any = None
    provenance: FieldProvenance = FieldProvenance.UNKNOWN_REQUIRES_USER
    # Optional reference to a SABAQ evidence record ID.
    # Qwen may populate this when proposing a value drawn from historical context.
    # The Provenance Firewall uses it to look up the exact SabaqEvidence record
    # and validate applicability before promoting to SABAQ_REUSED.
    # This field is NEVER trusted as authoritative — it is only a lookup hint.
    candidate_sabaq_reference_id: Optional[str] = None


class CatalogDraft(BaseModel):
    draft_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Base Identification
    product_code: DraftField = Field(default_factory=DraftField)
    sku_id: DraftField = Field(default_factory=DraftField)
    product_name: DraftField = Field(default_factory=DraftField)
    description: DraftField = Field(default_factory=DraftField)
    
    # Categorisation & Semantics
    product_type: DraftField = Field(default_factory=DraftField)
    brand: DraftField = Field(default_factory=DraftField)
    hsn_code: DraftField = Field(default_factory=DraftField)
    gst_percentage: DraftField = Field(default_factory=DraftField)
    
    # Physical Attributes
    fabric_type: DraftField = Field(default_factory=DraftField)
    care_instructions: DraftField = Field(default_factory=DraftField)
    set_composition: DraftField = Field(default_factory=DraftField)
    colour: DraftField = Field(default_factory=DraftField)
    size: DraftField = Field(default_factory=DraftField)
    size_type: DraftField = Field(default_factory=DraftField)
    pack_configuration: DraftField = Field(default_factory=DraftField)
    
    # Pricing
    mrp: DraftField = Field(default_factory=DraftField)
    selling_price: DraftField = Field(default_factory=DraftField)
    cost_price: DraftField = Field(default_factory=DraftField)
    
    # Packaging Dimensions
    packaging_length_cm: DraftField = Field(default_factory=DraftField)
    packaging_breadth_cm: DraftField = Field(default_factory=DraftField)
    packaging_height_cm: DraftField = Field(default_factory=DraftField)
    packaging_weight_kg: DraftField = Field(default_factory=DraftField)
    
    # Media
    sku_media_urls: DraftField = Field(default_factory=DraftField)
    product_media_urls: DraftField = Field(default_factory=DraftField)
    size_chart_url: DraftField = Field(default_factory=DraftField)
    video_urls: DraftField = Field(default_factory=DraftField)
    
    # Meta
    collection_tags: DraftField = Field(default_factory=DraftField)
    lifecycle_state: DraftField = Field(default_factory=DraftField)

    is_confirmed: bool = False

    # Set by extract_understanding() from _classify_scenario(cem_verification_result).
    # This is the AUTHORITATIVE runtime scenario — sourced from CEM, not from provenance
    # distribution, SABAQ, Qwen, or any static manifest value.
    # Values: "A" | "B" | "C" | "D" | None (not yet classified)
    cem_classified_scenario: Optional[str] = None

    firewall_diagnostics: Dict[str, Any] = Field(default_factory=dict)

    
    def get_missing_mandatory_fields(self) -> List[str]:
        missing = []
        # In a real implementation this list would be dynamically derived from AZM, 
        # but for this cognitive implementation step we define a core subset.
        mandatory = [
            'product_code', 'product_name', 'product_type', 'hsn_code', 'gst_percentage',
            'mrp', 'selling_price', 'cost_price', 'packaging_length_cm', 'packaging_breadth_cm', 
            'packaging_height_cm', 'packaging_weight_kg', 'sku_media_urls', 'colour'
        ]
        for field in mandatory:
            val = getattr(self, field, None)
            if not val or val.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER or val.value is None:
                missing.append(field)
        return missing


class ProposedCatalogAction(BaseModel):
    intent: CatalogIntent
    draft: CatalogDraft
    is_confirmed: bool = False
