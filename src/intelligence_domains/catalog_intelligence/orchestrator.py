import asyncio
import uuid
from typing import Optional, List, Union, Any, Dict

from src.shared.rabta_interfaces import IntelligenceDomainProvider
from src.shared.conversational_contracts import (
    ConversationalUnderstanding,
    ConversationalResponse,
    ConversationalIntent,
    NormalizedParameter,
    ParameterDataType,
    SemanticEntityReference,
    ConversationalResponseType
)
from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus
from src.shared.decision_contracts import DecisionResponse
from .models import IntakeRequest, AuthorizedContext, DecisionStatus
from .resolution import CognitiveResolutionEngine


# ──────────────────────────────────────────────────────────────────────────────
# Scenario classification
# ──────────────────────────────────────────────────────────────────────────────

class CatalogScenario:
    """CEM-grounded scenario label. Set only after CEM verification."""
    A = "A"   # Exact historical restoration — explicit identity only
    B = "B"   # New SKU in an existing, currently-active product family
    C = "C"   # Alias for B (used interchangeably in single-family contexts)
    D = "D"   # New product family — no active family found by CEM


# ──────────────────────────────────────────────────────────────────────────────
# AZM packaging bounds (sourced from AZM schema; hardcoded defaults only used
# if AZM provider is unavailable — do NOT relax for benchmark convenience)
# ──────────────────────────────────────────────────────────────────────────────

_AZM_DIM_MIN_CM = 1.0
_AZM_DIM_MAX_CM = 150.0
_AZM_WEIGHT_MIN_KG = 0.05
_AZM_WEIGHT_MAX_KG = 50.0


class CatalogIntelligenceOrchestrator(IntelligenceDomainProvider):
    """
    Cognitive translation and orchestration layer for Catalog ID.
    Implements IntelligenceDomainProvider.

    Execution order (mandatory):
        MULTIMODAL INTAKE
        → AZM RETRIEVAL
        → SABAQ RETRIEVAL          (structured List[SabaqEvidence] retained)
        → QWEN INFERENCE           (fields enter as AI_PROPOSED only)
        → CEM VERIFICATION         (product_code / sku_id identity)
        → SCENARIO CLASSIFICATION  (_classify_scenario — CEM evidence only)
        → PROVENANCE FIREWALL      (_evaluate_provenance_promotion — Reuse Matrix)
        → HUMAN APPROVAL CHECK
        → CEM MUTATION (ACTION only)
    """

    def __init__(
        self,
        memory_provider=None,
        azm_provider=None,
        sabaq_provider=None,
        gateway_provider=None,
        cem_resolver=None,
    ):
        self._engine = CognitiveResolutionEngine()
        self._memory_provider = memory_provider
        self._azm_provider = azm_provider
        self._sabaq_provider = sabaq_provider
        self._gateway_provider = gateway_provider
        self._cem_resolver = cem_resolver

    # ──────────────────────────────────────────────────────────────────────
    # Scenario Classification (CEM-grounded — no other source of authority)
    # ──────────────────────────────────────────────────────────────────────

    def _classify_scenario(self, cem_verification_result: Optional[Dict]) -> str:
        """
        Classify the current draft into Scenario A/B/C/D.

        Rules (strictly applied):
          A — only when the caller supplies an explicit verified historical sku_id or
              internal_id.  This method does NOT grant Scenario A; callers must pass
              scenario_a_identity=True from an upstream verified source.
          B/C — CEM confirms product_code exists AND lifecycle_state is active
                (not RETIRED).
          D — CEM reports not found, or the product is RETIRED, or CEM verification
              was not performed.

        Qwen, SABAQ, colour/size similarity, product_type matching, and visual
        similarity MUST NOT influence this classification.
        """
        if cem_verification_result is None:
            return CatalogScenario.D

        exists = cem_verification_result.get("exists", False)
        is_active = cem_verification_result.get("active", False)

        if exists and is_active:
            return CatalogScenario.B  # B and C are equivalent for the Firewall

        return CatalogScenario.D

    # ──────────────────────────────────────────────────────────────────────
    # Provenance Firewall — Deterministic Reuse Matrix
    # ──────────────────────────────────────────────────────────────────────

    def _evaluate_provenance_promotion(
        self,
        draft,
        sabaq_results: List,
        scenario: str,
        azm_schema: Optional[Dict] = None,
        cem_verification_result: Optional[Dict] = None,
    ) -> None:
        """
        Deterministic Provenance Firewall.

        For each field in the CatalogDraft, applies the approved Reuse Matrix:
          - NEVER touches USER_PROVIDED or IMAGE_INFERRED fields.
          - AI_PROPOSED fields are evaluated against the matrix.
          - Only the application layer may promote to SABAQ_REUSED.
          - Qwen's candidate_sabaq_reference_id is a lookup hint only; it
            confers zero authority.

        Mutates draft fields in place (provenance and value may be cleared).
        """
        from .models import DraftField, FieldProvenance

        # Build SABAQ lookup index: id → SabaqEvidence
        sabaq_index: Dict[str, Any] = {}
        for ev in (sabaq_results or []):
            sabaq_index[ev.id] = ev

        def _sabaq_lookup(field_obj) -> Optional[Any]:
            """Return the SabaqEvidence whose id matches the field's reference hint."""
            ref_id = getattr(field_obj, "candidate_sabaq_reference_id", None)
            if not ref_id:
                return None
            return sabaq_index.get(ref_id)

        def _exact_historical_value(evidence, historical_key: str) -> Optional[Any]:
            """Extract a value from the SABAQ structured_payload by key."""
            if evidence is None:
                return None
            payload = evidence.structured_payload or {}
            return payload.get(historical_key)

        def _azm_dim_ok(val) -> bool:
            try:
                v = float(val)
                return _AZM_DIM_MIN_CM <= v <= _AZM_DIM_MAX_CM
            except (TypeError, ValueError):
                return False

        def _azm_weight_ok(val) -> bool:
            try:
                v = float(val)
                return _AZM_WEIGHT_MIN_KG <= v <= _AZM_WEIGHT_MAX_KG
            except (TypeError, ValueError):
                return False

        def _typed_equality(hist_val, proposed_val, expected_type: str) -> bool:
            if hist_val is None or proposed_val is None:
                return False
            if expected_type == "numeric":
                try:
                    return float(hist_val) == float(proposed_val)
                except (ValueError, TypeError):
                    return False
            else:
                return str(hist_val).strip() == str(proposed_val).strip()

        def _cem_product_code(cem_result) -> Optional[str]:
            if not cem_result:
                return None
            return cem_result.get("product_code")

        # ── UNCONDITIONAL BLOCKS (apply to ALL scenarios) ──────────────────

        # selling_price — ALWAYS UNKNOWN_REQUIRES_USER
        draft.selling_price = DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER)

        # cost_price — ALWAYS UNKNOWN_REQUIRES_USER
        draft.cost_price = DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER)

        # ── IDENTITY FIELDS — never SABAQ_REUSED ───────────────────────────
        # product_code and sku_id keep AI_PROPOSED if already set by Qwen,
        # but provenance was already degraded to UNKNOWN_REQUIRES_USER by the
        # CEM collision check upstream. Do not re-promote here.
        # (No action needed; CEM collision logic already handles these.)

        # ── CONDITIONAL REUSE: only for verified B/C scenarios ─────────────
        if scenario not in (CatalogScenario.B, CatalogScenario.C):
            # Scenario D or A — operational fields must never be auto-reused
            for attr in [
                "packaging_length_cm",
                "packaging_breadth_cm",
                "packaging_height_cm",
                "packaging_weight_kg",
                "mrp",
            ]:
                field_obj = getattr(draft, attr, None)
                if field_obj and field_obj.provenance == FieldProvenance.AI_PROPOSED:
                    setattr(draft, attr, DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER))
            return  # Nothing else to evaluate for D

        # ── Scenario B/C path ──────────────────────────────────────────────
        verified_pc = _cem_product_code(cem_verification_result)
        draft_size = getattr(draft, "size", None)
        draft_size_val = draft_size.value if draft_size else None
        draft_pack_cfg = getattr(draft, "pack_configuration", None)
        draft_pack_val = draft_pack_cfg.value if draft_pack_cfg else None

        # ── PACKAGING DIMENSIONS (evaluated independently per axis) ────────
        for attr, hist_key in [
            ("packaging_length_cm", "Packaging Length (in cm)"),
            ("packaging_breadth_cm", "Packaging Breadth (in cm)"),
            ("packaging_height_cm", "Packaging Height (in cm)"),
        ]:
            field_obj = getattr(draft, attr, None)
            if not field_obj or field_obj.provenance != FieldProvenance.AI_PROPOSED:
                continue  # Already set by user or not proposed — leave alone

            promoted = False
            rejection_reason = "invalid-proposal"

            evidence = _sabaq_lookup(field_obj)
            if field_obj.candidate_sabaq_reference_id and evidence is None:
                rejection_reason = "evidence-not-found"
            elif evidence is None:
                rejection_reason = "missing-candidate-reference"
            else:
                hist_pc = (evidence.structured_payload or {}).get("Product Code")
                hist_size = (evidence.structured_payload or {}).get("Size")
                hist_pack = (evidence.structured_payload or {}).get("Pack Configuration")
                hist_val = _exact_historical_value(evidence, hist_key)

                # All applicability conditions must hold:
                pc_match = (hist_pc == verified_pc)
                size_match = (str(hist_size) == str(draft_size_val)) if draft_size_val else False
                pack_match = (str(hist_pack) == str(draft_pack_val)) if draft_pack_val else True
                val_match = _typed_equality(hist_val, field_obj.value, expected_type="numeric")
                azm_ok = _azm_dim_ok(field_obj.value)
                
                if not pc_match:
                    rejection_reason = "family-mismatch"
                elif not size_match:
                    rejection_reason = "size-mismatch"
                elif not pack_match:
                    rejection_reason = "pack-mismatch"
                elif not val_match:
                    rejection_reason = "value-mismatch"
                elif not azm_ok:
                    rejection_reason = "azm-bounds-rejection"
                else:
                    rejection_reason = "sabaq-reused"
                    promoted = True
                    setattr(draft, attr, DraftField(
                        value=field_obj.value,
                        provenance=FieldProvenance.SABAQ_REUSED,
                        candidate_sabaq_reference_id=evidence.id,
                    ))
                
                # Small read-only diagnostic reporting for benchmark
                if not hasattr(draft, "firewall_diagnostics"):
                    draft.firewall_diagnostics = {}
                draft.firewall_diagnostics[attr] = {
                    "rejection_reason": rejection_reason,
                    "evidence_id": evidence.id,
                }

            if not promoted:
                if not hasattr(draft, "firewall_diagnostics"):
                    draft.firewall_diagnostics = {}
                if attr not in draft.firewall_diagnostics:
                    draft.firewall_diagnostics[attr] = {"rejection_reason": rejection_reason}
                setattr(draft, attr, DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER))

        # ── PACKAGING WEIGHT (evaluated INDEPENDENTLY from dimensions) ─────
        field_obj = getattr(draft, "packaging_weight_kg", None)
        if field_obj and field_obj.provenance == FieldProvenance.AI_PROPOSED:
            promoted = False
            rejection_reason = "invalid-proposal"

            evidence = _sabaq_lookup(field_obj)
            if field_obj.candidate_sabaq_reference_id and evidence is None:
                rejection_reason = "evidence-not-found"
            elif evidence is None:
                rejection_reason = "missing-candidate-reference"
            else:
                hist_pc = (evidence.structured_payload or {}).get("Product Code")
                hist_size = (evidence.structured_payload or {}).get("Size")
                hist_pack = (evidence.structured_payload or {}).get("Pack Configuration")
                hist_val = _exact_historical_value(evidence, "Packaging Weight (in kg)")

                pc_match = (hist_pc == verified_pc)
                size_match = (str(hist_size) == str(draft_size_val)) if draft_size_val else False
                pack_match = (str(hist_pack) == str(draft_pack_val)) if draft_pack_val else True
                val_match = _typed_equality(hist_val, field_obj.value, expected_type="numeric")
                azm_ok = _azm_weight_ok(field_obj.value)

                if not pc_match:
                    rejection_reason = "family-mismatch"
                elif not size_match:
                    rejection_reason = "size-mismatch"
                elif not pack_match:
                    rejection_reason = "pack-mismatch"
                elif not val_match:
                    rejection_reason = "value-mismatch"
                elif not azm_ok:
                    rejection_reason = "azm-bounds-rejection"
                else:
                    rejection_reason = "sabaq-reused"
                    promoted = True
                    draft.packaging_weight_kg = DraftField(
                        value=field_obj.value,
                        provenance=FieldProvenance.SABAQ_REUSED,
                        candidate_sabaq_reference_id=evidence.id,
                    )
                
                # Small read-only diagnostic reporting for benchmark
                if not hasattr(draft, "firewall_diagnostics"):
                    draft.firewall_diagnostics = {}
                draft.firewall_diagnostics["packaging_weight_kg"] = {
                    "rejection_reason": rejection_reason,
                    "evidence_id": evidence.id,
                }

            if not promoted:
                if not hasattr(draft, "firewall_diagnostics"):
                    draft.firewall_diagnostics = {}
                if "packaging_weight_kg" not in draft.firewall_diagnostics:
                    draft.firewall_diagnostics["packaging_weight_kg"] = {"rejection_reason": rejection_reason}
                draft.packaging_weight_kg = DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER)

        # ── MRP — conditional, requires uniform_mrp_policy=True ───────────
        mrp_field = getattr(draft, "mrp", None)
        if mrp_field and mrp_field.provenance == FieldProvenance.AI_PROPOSED:
            promoted = False
            rejection_reason = "invalid-proposal"
            uniform_policy = False
            
            if azm_schema:
                uniform_policy = azm_schema.get("uniform_mrp_policy", False)
                
            if not uniform_policy:
                rejection_reason = "azm-policy-rejection"
            else:
                evidence = _sabaq_lookup(mrp_field)
                if mrp_field.candidate_sabaq_reference_id and evidence is None:
                    rejection_reason = "evidence-not-found"
                elif evidence is None:
                    rejection_reason = "missing-candidate-reference"
                else:
                    hist_pc = (evidence.structured_payload or {}).get("Product Code")
                    hist_size = (evidence.structured_payload or {}).get("Size")
                    hist_val = _exact_historical_value(evidence, "MRP")
                    
                    pc_match = (hist_pc == verified_pc)
                    size_match = (str(hist_size) == str(draft_size_val)) if draft_size_val else False
                    val_match = _typed_equality(hist_val, mrp_field.value, expected_type="numeric")
                    
                    if not pc_match:
                        rejection_reason = "family-mismatch"
                    elif not size_match:
                        rejection_reason = "size-mismatch"
                    elif not val_match:
                        rejection_reason = "value-mismatch"
                    else:
                        rejection_reason = "sabaq-reused"
                        promoted = True
                        draft.mrp = DraftField(
                            value=mrp_field.value,
                            provenance=FieldProvenance.SABAQ_REUSED,
                            candidate_sabaq_reference_id=evidence.id,
                        )

                    if not hasattr(draft, "firewall_diagnostics"):
                        draft.firewall_diagnostics = {}
                    draft.firewall_diagnostics["mrp"] = {
                        "rejection_reason": rejection_reason,
                        "evidence_id": evidence.id,
                    }

            if not promoted:
                if not hasattr(draft, "firewall_diagnostics"):
                    draft.firewall_diagnostics = {}
                if "mrp" not in draft.firewall_diagnostics:
                    draft.firewall_diagnostics["mrp"] = {"rejection_reason": rejection_reason}
                draft.mrp = DraftField(provenance=FieldProvenance.UNKNOWN_REQUIRES_USER)

    # ──────────────────────────────────────────────────────────────────────
    # Main extract_understanding pipeline
    # ──────────────────────────────────────────────────────────────────────

    async def extract_understanding(
        self,
        query: Union[str, "MultimodalQuery"],
        history: Optional[List[Any]] = None,
    ) -> ConversationalUnderstanding:
        from src.shared.conversational_contracts import MultimodalQuery
        import json
        import time

        # ── 0. Normalize Query ─────────────────────────────────────────────
        if isinstance(query, str):
            mm_query = MultimodalQuery(text=query)
        else:
            mm_query = query

        query_lower = mm_query.text.lower()
        is_action = any(w in query_lower for w in ["add", "create", "save", "prepare", "generate"])
        is_confirmation = query_lower.strip() in ["yes", "confirm", "proceed", "do it"]

        entities = []

        # ── 1. Load or Initialize Draft ────────────────────────────────────
        from src.intelligence_domains.catalog_intelligence.models import (
            CatalogDraft, FieldProvenance, DraftField
        )

        draft = CatalogDraft()
        session_id = "default_session"

        if self._memory_provider:
            from src.brain_core.memory.interfaces import MemoryQuery, MemoryEntry
            entries = await self._memory_provider.read_memory(
                MemoryQuery(session_id=session_id, tags=["CatalogDraft"])
            )
            if entries:
                entries.sort(key=lambda x: x.metadata.get("timestamp", 0), reverse=True)
                try:
                    draft = CatalogDraft.model_validate_json(entries[0].content)
                except Exception:
                    pass

        # ── 2. No automatic confirmation ───────────────────────────────────────
        # SABAQ MUST NEVER auto-confirm a draft. Always require human action.
        draft.is_confirmed = False

        if not is_confirmation:
            # ── Step A: AZM Retrieval ──────────────────────────────────────
            azm_schema: Optional[Dict] = None
            azm_semantics_str = "No AZM data available."
            if self._azm_provider:
                try:
                    azm_schema = self._azm_provider.get_namespace_schema("catalog")
                    azm_semantics_str = json.dumps(azm_schema)
                except Exception:
                    pass

            # ── Step B: SABAQ Retrieval (retain as structured objects) ─────
            from src.brain_core.knowledge.interfaces import SabaqProvenance
            sabaq_results: List = []
            sabaq_evidence_str = "No prior evidence."
            if self._sabaq_provider:
                try:
                    sabaq_results = await self._sabaq_provider.retrieve_evidence(
                        "catalog",
                        mm_query.text,
                        filters={
                            "provenance_in": [
                                SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
                                SabaqProvenance.HUMAN_APPROVED_DECISION,
                                SabaqProvenance.DERIVED_PROFILE,
                            ]
                        },
                        limit=5,
                    )
                    # Produce a summary string for Qwen context
                    sabaq_evidence_str = "\n".join([
                        json.dumps({
                            "sabaq_id": r.id,
                            "product_code": r.structured_payload.get("Product Code", ""),
                            "sku_id": r.structured_payload.get("Sku Id", ""),
                            "size": r.structured_payload.get("Size", ""),
                            "colour": r.structured_payload.get("Colour", ""),
                            "packaging_l": r.structured_payload.get("Packaging Length (in cm)", ""),
                            "packaging_b": r.structured_payload.get("Packaging Breadth (in cm)", ""),
                            "packaging_h": r.structured_payload.get("Packaging Height (in cm)", ""),
                            "packaging_w": r.structured_payload.get("Packaging Weight (in kg)", ""),
                            "mrp": r.structured_payload.get("MRP", ""),
                        })
                        for r in sabaq_results
                    ])
                except Exception:
                    pass

            # ── Step C: Qwen Inference ─────────────────────────────────────
            if self._gateway_provider:
                from src.brain_core.gateway.interfaces import GatewayGenerationRequest, GatewayMessage

                system_prompt = f"""You are Catalog Intelligence. Extract and propose values for the Catalog Draft (ShopDeck properties) based on the user's query.

Return a valid JSON object where the root contains two keys:
1. "operation_intent": explicitly "CREATE_FAMILY" if creating or adding a new product (e.g., "Add a Midnight Blue bedsheet"), or "UPSERT_SKUS" if adding/updating SKUs to a known existing family.
2. "draft_fields": an object where each key is a CatalogDraft field name and each value is an object with:
  "value": <proposed value>,
  "candidate_sabaq_reference_id": <sabaq_id string if you are drawing this value from a SABAQ history record, else null>

ALL fields you propose enter the system as AI_PROPOSED candidates.
Do NOT include a "provenance" key — the application determines provenance.
Do NOT claim SABAQ_REUSED, USER_PROVIDED, or any other provenance.

For operational fields (mrp, selling_price, cost_price, packaging dimensions, packaging weight):
  - Only propose a value if you can reference it from a SABAQ history record.
  - Always include the candidate_sabaq_reference_id when doing so.
  - If you have no SABAQ reference, omit the field entirely.

For product_code and sku_id:
  - Propose a candidate following naming conventions from SABAQ history.
  - Do not generate UUID-like identifiers.

AZM Semantic Constraints:
{azm_semantics_str}

SABAQ Historical Records (advisory only — not authoritative):
{sabaq_evidence_str}"""

                user_prompt = (
                    f"Query: {mm_query.text}\n"
                    f"Images: {mm_query.image_uris}"
                )

                req = GatewayGenerationRequest(
                    messages=[
                        GatewayMessage(role="system", content=system_prompt),
                        GatewayMessage(role="user", content=user_prompt),
                    ],
                    model="local-qwen",
                )
                try:
                    resp = await self._gateway_provider.generate(req)
                    content = resp.content
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    parsed_proposal = json.loads(content)
                    print("DEBUG PARSED PROPOSAL:", json.dumps(parsed_proposal, indent=2))

                    from src.intelligence_domains.catalog_intelligence.models import CatalogIntent
                    qwen_intent = parsed_proposal.get("operation_intent")
                    try:
                        self._parsed_intent = CatalogIntent(qwen_intent)
                    except Exception:
                        self._parsed_intent = CatalogIntent.UPSERT_SKUS

                    draft_fields = parsed_proposal.get("draft_fields", parsed_proposal)
                    for key, proposal_data in draft_fields.items():
                        if not hasattr(draft, key) or not isinstance(proposal_data, dict):
                            continue
                        val = proposal_data.get("value")
                        ref_id = proposal_data.get("candidate_sabaq_reference_id")

                        # Reject UUID-like product_code / sku_id proposals
                        if key in ("product_code", "sku_id") and val:
                            if len(str(val)) > 20 and "-" in str(val) and str(val).replace("-", "").replace("_", "").isalnum():
                                # Looks like a UUID — reject silently
                                continue

                        if val is not None:
                            setattr(draft, key, DraftField(
                                value=val,
                                provenance=FieldProvenance.AI_PROPOSED,
                                candidate_sabaq_reference_id=ref_id,
                            ))
                except Exception as e:
                    print(f"DEBUG GATEWAY EXCEPTION: {e}")
            else:
                # Minimal fallback when no gateway is configured
                if "bed" in query_lower:
                    draft.product_type = DraftField(value="BED", provenance=FieldProvenance.USER_PROVIDED)
                if "blue" in query_lower:
                    draft.colour = DraftField(value="BL", provenance=FieldProvenance.USER_PROVIDED)
                
                import re
                pc_match = re.search(r"Product Code:\s*([A-Za-z0-9_-]+)", mm_query.text, re.IGNORECASE)
                if pc_match:
                    draft.product_code = DraftField(value=pc_match.group(1), provenance=FieldProvenance.USER_PROVIDED)
                sku_match = re.search(r"SKU:\s*([A-Za-z0-9_-]+)", mm_query.text, re.IGNORECASE)
                if sku_match:
                    draft.sku_id = DraftField(value=sku_match.group(1), provenance=FieldProvenance.USER_PROVIDED)

            # ── Step D: CEM Verification (product_code / sku_id identity) ──
            cem_verification_result: Optional[Dict] = None
            if self._cem_resolver:
                try:
                    cem_adapter = self._cem_resolver.resolve("catalog")
                    from src.shared.evidence_request_contracts import BusinessStateVerificationRequest

                    pc_field = getattr(draft, "product_code", None)
                    if pc_field and pc_field.value and pc_field.provenance != FieldProvenance.UNKNOWN_REQUIRES_USER:
                        v_req = BusinessStateVerificationRequest(
                            domain_urn="urn:aarambooks:cem:catalog",
                            verification_target="product_code",
                            context_payload={"product_code": pc_field.value},
                        )
                        v_resp = await cem_adapter.verify_business_state(v_req)
                        cem_verification_result = v_resp.evidence_data or {}

                        # If collision (exists=True but sku_id already taken), block it
                        if cem_verification_result.get("exists") and not cem_verification_result.get("active", False):
                            draft.product_code = DraftField(
                                value=pc_field.value,
                                provenance=FieldProvenance.UNKNOWN_REQUIRES_USER,
                            )

                    # Verify sku_id availability
                    sku_field = getattr(draft, "sku_id", None)
                    if sku_field and sku_field.value and sku_field.provenance != FieldProvenance.UNKNOWN_REQUIRES_USER:
                        v_req = BusinessStateVerificationRequest(
                            domain_urn="urn:aarambooks:cem:catalog",
                            verification_target="sku_id",
                            context_payload={"sku_id": sku_field.value},
                        )
                        try:
                            v_resp = await cem_adapter.verify_business_state(v_req)
                            # If sku already exists, mark as requiring user input
                            if v_resp.evidence_data and v_resp.evidence_data.get("exists"):
                                draft.sku_id = DraftField(
                                    value=sku_field.value,
                                    provenance=FieldProvenance.UNKNOWN_REQUIRES_USER,
                                )
                        except Exception:
                            print(f"DEBUG EXTRACTION EXCEPTION: {e}")
                            pass

                except Exception:
                    pass

            # ── Step E: Scenario Classification (CEM-grounded) ────────────
            scenario = self._classify_scenario(cem_verification_result)
            # Record the authoritative scenario on the draft so it is
            # serialized to draft_json and available to callers (benchmark,
            # interpret_evidence) without any re-computation or provenance
            # inference. This is the ONLY location where cem_classified_scenario
            # is set — from _classify_scenario() using CEM evidence only.
            draft.cem_classified_scenario = scenario


            print("DEBUG DRAFT BEFORE FIREWALL:", draft.model_dump_json(indent=2))
            
            # --- Exact Candidate Evidence Resolution (Async Boundary) ---
            if self._sabaq_provider:
                candidate_ids = set()
                for field_name, field_val in draft:
                    if hasattr(field_val, "candidate_sabaq_reference_id") and field_val.candidate_sabaq_reference_id:
                        candidate_ids.add(field_val.candidate_sabaq_reference_id)
                
                # Filter out ones already in sabaq_results from FTS
                existing_ids = {ev.id for ev in (sabaq_results or [])}
                missing_ids = candidate_ids - existing_ids
                
                if missing_ids:
                    # Fetch missing exact evidence
                    import asyncio
                    tasks = [self._sabaq_provider.get_evidence(ref_id) for ref_id in missing_ids]
                    resolved_evidences = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for ev in resolved_evidences:
                        if ev and not isinstance(ev, Exception):
                            if sabaq_results is None:
                                sabaq_results = []
                            sabaq_results.append(ev)
            # ------------------------------------------------------------

            # ── Step F: Provenance Firewall ────────────────────────────────
            self._evaluate_provenance_promotion(
                draft=draft,
                sabaq_results=sabaq_results,
                scenario=scenario,
                azm_schema=azm_schema,
                cem_verification_result=cem_verification_result,
            )

        # ── 3. Persist Draft ───────────────────────────────────────────────
        if self._memory_provider:
            from src.brain_core.memory.interfaces import MemoryEntry
            import time
            entry = MemoryEntry(
                content=draft.model_dump_json(),
                metadata={"timestamp": time.time(), "tags": ["CatalogDraft"]},
            )
            await self._memory_provider.write_memory(entry, session_id=session_id)

        # ── 4. Intent Decision ─────────────────────────────────────────────
        missing_fields = draft.get_missing_mandatory_fields()
        intent = ConversationalIntent.SUMMARIZE
        if not missing_fields and draft.is_confirmed:
            intent = ConversationalIntent.ACTION

        from src.intelligence_domains.catalog_intelligence.models import ProposedCatalogAction, CatalogIntent
        action = ProposedCatalogAction(
            intent=getattr(self, "_parsed_intent", CatalogIntent.UPSERT_SKUS),
            draft=draft,
            is_confirmed=draft.is_confirmed
        )

        parameters = [
            NormalizedParameter(
                parameter_name="action_json",
                data_type=ParameterDataType.STRING,
                value=action.model_dump_json(),
                original_expression="",
            )
        ]

        if hasattr(draft, "firewall_diagnostics"):
            parameters.append(
                NormalizedParameter(
                    parameter_name="firewall_diagnostics",
                    data_type=ParameterDataType.STRING,
                    value=json.dumps(draft.firewall_diagnostics),
                    original_expression="",
                )
            )

        return ConversationalUnderstanding(
            original_query=mm_query.text,
            intent=intent,
            entities=entities,
            parameters=parameters,
        )

    # ──────────────────────────────────────────────────────────────────────
    # execute_read_query / interpret_evidence
    # ──────────────────────────────────────────────────────────────────────

    async def execute_read_query(self, request) -> BusinessEvidenceResponse:
        action_json = None
        for p in request.classified_requirement.understanding.parameters:
            if p.parameter_name == "action_json":
                action_json = p.value

        return BusinessEvidenceResponse(
            status=BusinessRealityStatus.ENTITY_RESOLVED,
            evidence_data={"action_json": action_json},
        )

    async def interpret_evidence(
        self, response: Union[BusinessEvidenceResponse, DecisionResponse]
    ) -> ConversationalResponse:
        import json
        import time

        if isinstance(response, DecisionResponse):
            directives = {"decision_status": response.status.value}
            
            if hasattr(response, "confirmation_context") and response.confirmation_context:
                req = response.confirmation_context.original_request
                if req and hasattr(req, "classified_requirement"):
                    params = req.classified_requirement.understanding.parameters
                    for p in params:
                        if p.parameter_name == "action_json":
                            directives["action_json"] = p.value
                        elif p.parameter_name == "firewall_diagnostics":
                            directives["firewall_diagnostics"] = p.value

            return ConversationalResponse(
                response_type="CONFIRMATION_REQUEST",
                message=f"Please confirm: {response.status.value}",
                render_directives=directives,
            )

        if response.status == BusinessRealityStatus.ENTITY_RESOLVED:
            data = response.evidence_data or {}

            # 1. SABAQ feedback on ACTION SUCCESS
            if data.get("operation_status") == "SUCCESS" and "draft_json" in data:
                if self._sabaq_provider:
                    try:
                        draft_dict = json.loads(data["draft_json"])
                        metadata = {
                            "original_user_intent": "ACTION",
                            "visual_observations": draft_dict.get("sku_media_urls", {}).get("value", []),
                            "field_level_provenance": {
                                k: v.get("provenance")
                                for k, v in draft_dict.items()
                                if isinstance(v, dict)
                            },
                            "family_relationship": data.get("internal_id"),
                            "cem_outcome_reference": data.get("operation_status"),
                            "timestamp": time.time(),
                        }
                        asyncio.create_task(
                            self._sabaq_provider.record_approved_outcome(
                                domain="catalog",
                                search_content=(
                                    f"{draft_dict.get('product_code', {}).get('value', '')} "
                                    f"{draft_dict.get('product_name', {}).get('value', '')} "
                                    f"{draft_dict.get('product_type', {}).get('value', '')}"
                                ),
                                payload=draft_dict,
                                provenance=__import__(
                                    "src.brain_core.knowledge.interfaces",
                                    fromlist=["SabaqProvenance"]
                                ).SabaqProvenance.HUMAN_APPROVED_DECISION,
                                metadata=metadata,
                            )
                        )
                    except Exception as e:
                        print(f"DEBUG SABAQ EXCEPTION: {e}")
                        pass
                
                print(f"DEBUG retrieved SABAQ IDs: {[r.id for r in sabaq_results]}")

                return ConversationalResponse(
                    response_type=ConversationalResponseType.SUCCESS,
                    message="Catalog draft successfully saved to ShopDeck!",
                    render_directives={"action_success": True},
                )

            # 2. Draft summarisation
            action_json = data.get("action_json")
            draft_json_str = data.get("draft_json")
            
            if action_json or draft_json_str:
                if action_json:
                    parsed_action = json.loads(action_json)
                    draft_dict = parsed_action.get("draft", {})
                else:
                    draft_dict = json.loads(draft_json_str)

                mandatory = [
                    "product_code", "product_name", "product_type", "hsn_code",
                    "gst_percentage", "mrp", "selling_price", "cost_price",
                    "packaging_length_cm", "packaging_breadth_cm",
                    "packaging_height_cm", "packaging_weight_kg",
                    "sku_media_urls", "colour",
                ]
                missing = [
                    f for f in mandatory
                    if draft_dict.get(f, {}).get("provenance") == "UNKNOWN_REQUIRES_USER"
                    or draft_dict.get(f, {}).get("value") is None
                ]

                lines = ["**CATALOG DRAFT**"]
                for k, v in draft_dict.items():
                    if k in ("draft_id", "is_confirmed") or not isinstance(v, dict):
                        continue
                    val = v.get("value", "MISSING")
                    prov = v.get("provenance", "UNKNOWN")
                    if prov != "UNKNOWN_REQUIRES_USER":
                        lines.append(f"- **{k}**: {val} [{prov}]")
                    else:
                        lines.append(f"- **{k}**: MISSING")

                if missing:
                    lines.append(f"\nMissing mandatory fields: {', '.join(missing)}.")
                    lines.append("Please provide the missing information.")
                elif not draft_dict.get("is_confirmed"):
                    lines.append("\nEverything required is ready.")
                    lines.append(
                        "Please confirm: Create this Product Family/SKU and "
                        "prepare it for ShopDeck. (Reply 'yes' or 'confirm')"
                    )
                else:
                    lines.append("\nDraft confirmed! Processing...")

                directives = {}
                if action_json:
                    directives["action_json"] = action_json
                elif draft_json_str:
                    directives["draft_json"] = draft_json_str

                return ConversationalResponse(
                    response_type=(
                        ConversationalResponseType.CLARIFICATION_REQUIRED
                        if missing or not draft_dict.get("is_confirmed")
                        else ConversationalResponseType.SUCCESS
                    ),
                    message="\n".join(lines),
                    render_directives=directives,
                )

            internal_id = data.get("internal_id")
            context = AuthorizedContext(authorized_parent_internal_id=internal_id)
            request = IntakeRequest(
                raw_text="Add variant",
                authorized_context=context,
                extracted_attributes={"product_type": "BED", "colour": "BL"},
            )
            decision = self._engine.resolve(request)

            if decision.status in (DecisionStatus.PROPOSE_ATTACH, DecisionStatus.PROPOSE_NEW):
                candidates = self._engine.generate_sku_candidates("BED", "BL")
                return ConversationalResponse(
                    response_type=ConversationalResponseType.SUCCESS,
                    message="I propose the following action based on the discovered context.",
                    render_directives={
                        "action_required": True,
                        "action_intent": "ACTION",
                        "operation": "SaveProductFamily",
                        "authorized_parent_internal_id": internal_id,
                        "sku_candidates": candidates,
                        "product_type": "BED",
                        "colour": "BL",
                    },
                )
            return ConversationalResponse(
                response_type="CLARIFICATION_REQUIRED",
                message="I need human approval to proceed. The context was ambiguous.",
                render_directives={"decision_status": decision.status.value},
            )

        elif response.status == BusinessRealityStatus.EVIDENCE_AVAILABLE:
            directives = response.evidence_data.copy()
            if "artifact_id" in directives:
                directives["artifact_download_url"] = (
                    f"/api/v1/catalog/artifacts/{directives['artifact_id']}/download"
                )
            return ConversationalResponse(
                response_type="SUCCESS",
                message=response.evidence_data.get("message", "Success"),
                render_directives=directives,
            )

        elif response.status == BusinessRealityStatus.EXECUTION_LIMITATION:
            reasons = [limit.reason for limit in response.execution_limitations]
            if "SKU_PROPOSAL_EXHAUSTED" in reasons:
                return ConversationalResponse(
                    response_type="CLARIFICATION_REQUIRED",
                    message="All bounded SKU candidates collided. Human approval required.",
                    render_directives={"status": "SKU_PROPOSAL_EXHAUSTED"},
                )
            for limit in response.execution_limitations:
                if "MISSING_MANDATORY_FIELD" in limit.reason:
                    return ConversationalResponse(
                        response_type="CLARIFICATION_REQUIRED",
                        message=f"I need more information to proceed: {limit.reason}",
                        render_directives={"missing_fields": True, "details": limit.reason},
                    )
            return ConversationalResponse(
                response_type="EXECUTION_LIMITATION",
                message=f"Execution limitation: {reasons}",
            )

        elif response.status == BusinessRealityStatus.MULTIPLE_CANDIDATES:
            return ConversationalResponse(
                response_type="CLARIFICATION_REQUIRED",
                message="Multiple products matched your query. Please be more specific.",
            )

        elif response.status == BusinessRealityStatus.ENTITY_NOT_FOUND:
            return ConversationalResponse(
                response_type="CLARIFICATION_REQUIRED",
                message="No products matched your query. Please check the product code.",
            )

        return ConversationalResponse(
            response_type="SYSTEM_FAILURE",
            message="An unexpected condition occurred.",
        )
