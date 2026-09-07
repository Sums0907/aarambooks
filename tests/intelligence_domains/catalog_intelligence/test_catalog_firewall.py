"""
Phase 5B Provenance Firewall & Scenario Classification Tests.

These tests verify:
  - CEM-grounded scenario classification
  - Unconditional field blocks (selling_price, cost_price)
  - Conditional SABAQ_REUSED promotion (packaging dims/weight)
  - MRP never promoted without uniform_mrp_policy
  - UUID-like SKU rejection
  - Scenario A requires explicit identity
  - Empirical regression: 101MP must not inherit 104MP packaging
  - Empirical regression: 116BS must not inherit 102BS MRP
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.intelligence_domains.catalog_intelligence.orchestrator import (
    CatalogIntelligenceOrchestrator,
    CatalogScenario,
)
from src.intelligence_domains.catalog_intelligence.models import (
    CatalogDraft,
    DraftField,
    FieldProvenance,
    ProposedCatalogAction,
)
from src.brain_core.knowledge.interfaces import SabaqEvidence, SabaqProvenance
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_evidence(
    ev_id: str,
    product_code: str,
    size: str,
    packaging_l=None,
    packaging_b=None,
    packaging_h=None,
    packaging_w=None,
    mrp=None,
    pack_configuration=None,
) -> SabaqEvidence:
    payload = {
        "Product Code": product_code,
        "Size": size,
    }
    if packaging_l is not None:
        payload["Packaging Length (in cm)"] = str(packaging_l)
    if packaging_b is not None:
        payload["Packaging Breadth (in cm)"] = str(packaging_b)
    if packaging_h is not None:
        payload["Packaging Height (in cm)"] = str(packaging_h)
    if packaging_w is not None:
        payload["Packaging Weight (in kg)"] = str(packaging_w)
    if mrp is not None:
        payload["MRP"] = str(mrp)
    if pack_configuration is not None:
        payload["Pack Configuration"] = pack_configuration
    return SabaqEvidence(
        id=ev_id,
        domain_namespace="catalog",
        provenance=SabaqProvenance.BUSINESS_SYSTEM_HISTORY,
        evidence_version=1,
        search_content="test",
        structured_payload=payload,
        metadata={},
        source_reference=product_code,
    )


def _make_draft_with_field(field_name: str, value, ref_id: str = None) -> CatalogDraft:
    draft = CatalogDraft()
    setattr(draft, field_name, DraftField(
        value=value,
        provenance=FieldProvenance.AI_PROPOSED,
        candidate_sabaq_reference_id=ref_id,
    ))
    return draft


def _orchestrator() -> CatalogIntelligenceOrchestrator:
    return CatalogIntelligenceOrchestrator()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scenario Classification — CEM-grounded only
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioClassification:

    def test_scenario_classification_requires_cem(self):
        """Without CEM verification result, scenario must default to D."""
        o = _orchestrator()
        assert o._classify_scenario(None) == CatalogScenario.D

    def test_scenario_d_when_product_not_found(self):
        """CEM returns exists=False → Scenario D."""
        o = _orchestrator()
        cem_result = {"exists": False, "active": False, "product_code": "NEW-PC"}
        assert o._classify_scenario(cem_result) == CatalogScenario.D

    def test_scenario_bc_when_product_found_and_active(self):
        """CEM returns exists=True + active=True → Scenario B/C."""
        o = _orchestrator()
        cem_result = {
            "exists": True,
            "active": True,
            "product_code": "TLS-MP-CB-DBF",
            "lifecycle_state": "READY",
        }
        assert o._classify_scenario(cem_result) == CatalogScenario.B

    def test_scenario_d_when_product_retired(self):
        """CEM returns exists=True but active=False (RETIRED) → Scenario D."""
        o = _orchestrator()
        cem_result = {
            "exists": True,
            "active": False,
            "product_code": "OLD-PC",
            "lifecycle_state": "RETIRED",
        }
        assert o._classify_scenario(cem_result) == CatalogScenario.D

    def test_scenario_a_requires_explicit_identity(self):
        """
        Scenario A is NOT assignable by _classify_scenario.
        Visual/semantic similarity must never establish exact historical identity.
        """
        o = _orchestrator()
        # Even if CEM finds a match, _classify_scenario returns B not A
        cem_result = {"exists": True, "active": True, "product_code": "TLS-MP-CB-DBF"}
        result = o._classify_scenario(cem_result)
        assert result != CatalogScenario.A, (
            "Scenario A must never be granted by _classify_scenario — "
            "it requires an explicit upstream identity assertion."
        )

    def test_sabaq_cannot_establish_scenario_bc(self):
        """SABAQ evidence alone must not change _classify_scenario() from D."""
        o = _orchestrator()
        # Even if SABAQ contains matching evidence, scenario classification is CEM-only
        cem_result = {"exists": False, "active": False, "product_code": "NEW-PC"}
        assert o._classify_scenario(cem_result) == CatalogScenario.D

    def test_qwen_cannot_establish_scenario_bc(self):
        """A Qwen-proposed product_code matching historical SABAQ evidence must remain D until CEM verifies."""
        o = _orchestrator()
        # Qwen's proposed code is not a substitute for CEM verification
        cem_result = {"exists": False, "active": False, "product_code": "MATCHING-SABAQ-PC"}
        assert o._classify_scenario(cem_result) == CatalogScenario.D

    def test_new_sku_under_existing_product_code_is_scenario_b(self):
        """CEM verification of an existing active product_code with a new SKU establishes Scenario B."""
        o = _orchestrator()
        cem_result = {
            "exists": True,
            "active": True,
            "product_code": "TLS-MP-CB-DBF",
            "lifecycle_state": "PUBLISHED",
        }
        assert o._classify_scenario(cem_result) == CatalogScenario.B



# ─────────────────────────────────────────────────────────────────────────────
# 2. Unconditional Field Blocks
# ─────────────────────────────────────────────────────────────────────────────

class TestUnconditionalBlocks:

    def test_firewall_rejects_selling_price_always(self):
        """selling_price must always be UNKNOWN_REQUIRES_USER regardless of scenario or SABAQ."""
        o = _orchestrator()
        for scenario in [CatalogScenario.B, CatalogScenario.C, CatalogScenario.D]:
            draft = CatalogDraft()
            draft.selling_price = DraftField(value=1499, provenance=FieldProvenance.AI_PROPOSED)
            evidence = _make_evidence("ev1", "TLS-MP-CB-DBF", '72x78 + 12"', mrp=1499)
            o._evaluate_provenance_promotion(draft, [evidence], scenario)
            assert draft.selling_price.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
                f"selling_price must be UNKNOWN_REQUIRES_USER in Scenario {scenario}"
            )
            assert draft.selling_price.value is None

    def test_firewall_rejects_cost_price_always(self):
        """cost_price must always be UNKNOWN_REQUIRES_USER regardless of scenario or SABAQ."""
        o = _orchestrator()
        for scenario in [CatalogScenario.B, CatalogScenario.C, CatalogScenario.D]:
            draft = CatalogDraft()
            draft.cost_price = DraftField(value=700, provenance=FieldProvenance.AI_PROPOSED)
            evidence = _make_evidence("ev1", "TLS-MP-CB-DBF", '72x78 + 12"')
            o._evaluate_provenance_promotion(draft, [evidence], scenario)
            assert draft.cost_price.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
                f"cost_price must be UNKNOWN_REQUIRES_USER in Scenario {scenario}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Packaging Dimension Promotion
# ─────────────────────────────────────────────────────────────────────────────

class TestPackagingPromotion:

    def _bc_draft_with_all_dims(self, pc: str, size: str, l, b, h, w, ev_id: str):
        """Build a draft where all dims point to the same SABAQ record."""
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        for attr, val in [
            ("packaging_length_cm", l),
            ("packaging_breadth_cm", b),
            ("packaging_height_cm", h),
        ]:
            setattr(draft, attr, DraftField(
                value=val,
                provenance=FieldProvenance.AI_PROPOSED,
                candidate_sabaq_reference_id=ev_id,
            ))
        draft.packaging_weight_kg = DraftField(
            value=w,
            provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id=ev_id,
        )
        return draft

    def test_firewall_promotes_packaging_on_verified_family(self):
        """
        Packaging dims promoted to SABAQ_REUSED when:
          - Scenario B/C (CEM-verified)
          - SABAQ evidence product_code matches CEM-verified pc
          - size matches
          - candidate value exactly matches historical value
          - value within AZM bounds
        """
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'
        evidence = _make_evidence("ev-104mp", pc, size, packaging_l=33, packaging_b=27, packaging_h=11, packaging_w=1.3)
        draft = self._bc_draft_with_all_dims(pc, size, 33, 27, 11, 1.3, "ev-104mp")

        cem_result = {"exists": True, "active": True, "product_code": pc}
        o._evaluate_provenance_promotion(draft, [evidence], CatalogScenario.B, cem_verification_result=cem_result)

        assert draft.packaging_length_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_breadth_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_height_cm.provenance == FieldProvenance.SABAQ_REUSED

    def test_firewall_rejects_packaging_scenario_d(self):
        """Packaging dims from any SABAQ record must NOT be promoted in Scenario D."""
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'
        evidence = _make_evidence("ev-104mp", pc, size, packaging_l=33, packaging_b=27, packaging_h=11)
        draft = self._bc_draft_with_all_dims(pc, size, 33, 27, 11, 1.3, "ev-104mp")

        o._evaluate_provenance_promotion(draft, [evidence], CatalogScenario.D)

        assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
        assert draft.packaging_breadth_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
        assert draft.packaging_height_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

    def test_firewall_rejects_packaging_weight_independently(self):
        """
        Packaging weight is evaluated independently.
        Even if dimensions are promoted, weight must fail independently if its
        historical value does not exactly match the candidate value.
        """
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'
        # Evidence has weight=1.3 but draft proposes weight=2.5 (mismatch)
        evidence = _make_evidence("ev-104mp", pc, size, packaging_l=33, packaging_b=27, packaging_h=11, packaging_w=1.3)
        draft = self._bc_draft_with_all_dims(pc, size, 33, 27, 11, 2.5, "ev-104mp")  # weight mismatch

        cem_result = {"exists": True, "active": True, "product_code": pc}
        o._evaluate_provenance_promotion(draft, [evidence], CatalogScenario.B, cem_verification_result=cem_result)

        # Dims may be promoted but weight must not
        assert draft.packaging_weight_kg.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
            "Weight must be independently rejected when historical value doesn't match candidate"
        )

    def test_pack_configuration_absent_is_explicit_design_choice(self):
        """
        Design choice: when the CatalogDraft has no pack_configuration value,
        pack_match evaluates to True (the check is skipped).

        This is intentional — not all products define pack_configuration, and
        its absence should not unconditionally block SABAQ_REUSED promotion.

        CRITICAL: this relaxation does NOT bypass any of the other four required
        applicability conditions, which ALL continue to apply:
          1. Exact SABAQ record lookup via candidate_sabaq_reference_id
          2. CEM-verified product_code must match SABAQ record's Product Code
          3. Exact size match between draft and SABAQ record
          4. Candidate value must exactly match historical value from SABAQ payload
          5. Value must pass AZM bounds validation

        If any of conditions 1-5 fail, SABAQ_REUSED is NOT granted regardless of
        pack_configuration.

        A product with pack_configuration=None cannot bypass pc_match, size_match,
        val_match, or azm_ok.
        """
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'

        # Evidence has no Pack Configuration field — neither does the draft.
        evidence = _make_evidence(
            "ev-104mp", pc, size,
            packaging_l=33, packaging_b=27, packaging_h=11,
            # pack_configuration intentionally absent from evidence payload too
        )
        # Draft has no pack_configuration (default blank DraftField)
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        draft.packaging_length_cm = DraftField(
            value=33, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        draft.packaging_breadth_cm = DraftField(
            value=27, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        draft.packaging_height_cm = DraftField(
            value=11, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        # pack_configuration NOT set — draft.pack_configuration is blank DraftField

        cem_result = {"exists": True, "active": True, "product_code": pc}
        o._evaluate_provenance_promotion(
            draft, [evidence], CatalogScenario.B,
            cem_verification_result=cem_result
        )

        # All five conditions hold (pc_match, size_match, pack_match=True by design,
        # val_match, azm_ok) → promotion is granted. This is the intended behaviour.
        assert draft.packaging_length_cm.provenance == FieldProvenance.SABAQ_REUSED, (
            "When pack_configuration is absent from both draft and SABAQ, "
            "pack_match=True is the explicit design choice and promotion must succeed "
            "provided all other applicability conditions hold."
        )
        assert draft.packaging_breadth_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_height_cm.provenance == FieldProvenance.SABAQ_REUSED

    def test_pack_configuration_mismatch_blocks_promotion(self):
        """
        Complementary guard: when the draft DOES have a pack_configuration value
        and it does NOT match the SABAQ record's Pack Configuration,
        promotion must be blocked (pack_match=False → UNKNOWN_REQUIRES_USER).
        """
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'

        evidence = _make_evidence(
            "ev-104mp", pc, size,
            packaging_l=33, packaging_b=27, packaging_h=11,
            pack_configuration="1 Mattress Protector",
        )
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        # Draft has a DIFFERENT pack_configuration value
        draft.pack_configuration = DraftField(
            value="2 Mattress Protectors",
            provenance=FieldProvenance.AI_PROPOSED,
        )
        draft.packaging_length_cm = DraftField(
            value=33, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )

        cem_result = {"exists": True, "active": True, "product_code": pc}
        o._evaluate_provenance_promotion(
            draft, [evidence], CatalogScenario.B,
            cem_verification_result=cem_result
        )

        # pack_match=False because draft value != SABAQ value → must not promote
        assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
            "When draft pack_configuration is set and differs from SABAQ record, "
            "pack_match must be False and promotion must be blocked."
        )



# ─────────────────────────────────────────────────────────────────────────────
# 4. MRP — never auto-promoted without uniform_mrp_policy
# ─────────────────────────────────────────────────────────────────────────────

class TestMrpPromotion:

    def test_firewall_rejects_mrp_without_uniform_policy(self):
        """MRP must remain UNKNOWN_REQUIRES_USER when uniform_mrp_policy is absent."""
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'
        evidence = _make_evidence("ev-104mp", pc, size, mrp=2999)
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        draft.mrp = DraftField(
            value=2999, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        cem_result = {"exists": True, "active": True, "product_code": pc}

        # No azm_schema = no uniform_mrp_policy
        o._evaluate_provenance_promotion(draft, [evidence], CatalogScenario.B, cem_verification_result=cem_result)
        assert draft.mrp.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

    def test_firewall_rejects_mrp_even_with_false_uniform_policy(self):
        """MRP must remain UNKNOWN_REQUIRES_USER when uniform_mrp_policy=False."""
        o = _orchestrator()
        pc = "TLS-MP-CB-DBF"
        size = '72x78 + 12"'
        evidence = _make_evidence("ev-104mp", pc, size, mrp=2999)
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        draft.mrp = DraftField(
            value=2999, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        cem_result = {"exists": True, "active": True, "product_code": pc}

        o._evaluate_provenance_promotion(
            draft, [evidence], CatalogScenario.B,
            azm_schema={"uniform_mrp_policy": False},
            cem_verification_result=cem_result
        )
        assert draft.mrp.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER


# ─────────────────────────────────────────────────────────────────────────────
# 5. SKU Identity — reject UUID-like proposals
# ─────────────────────────────────────────────────────────────────────────────

class TestSkuIdentity:

    @pytest.mark.asyncio
    async def test_firewall_rejects_uuid_sku_proposal(self):
        """
        UUID-like sku_id proposals from Qwen must be dropped before entering the draft.
        A 36-character hyphenated hex string is UUID-like and must be rejected.
        """
        o = _orchestrator()

        mock_gateway = AsyncMock()
        mock_gateway.generate.return_value = MagicMock(
            content='{"sku_id": {"value": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "candidate_sabaq_reference_id": null}}'
        )
        o._gateway_provider = mock_gateway

        understanding = await o.extract_understanding("Add new blue mattress protector")

        import json
        params = {p.parameter_name: p.value for p in understanding.parameters}
        draft_dict = json.loads(params["action_json"])["draft"]
        sku_field = draft_dict.get("sku_id", {})
        assert sku_field.get("value") is None or sku_field.get("provenance") == "UNKNOWN_REQUIRES_USER", (
            "UUID-like sku_id must not be retained in the draft"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Empirical Regression: 101MP must NOT inherit 104MP packaging
# ─────────────────────────────────────────────────────────────────────────────

class TestEmpiricalRegressions:

    def test_101mp_does_not_inherit_104mp_packaging(self):
        """
        Real data:
          104MP (TLS-MP-CB-DBF): 33×27×11 cm, 1.3kg
          101MP (TLS-MP-RYB-DBF): 23×23×23 cm, 3.0kg

        Even though both share size=72x78+12" and the same semantic family,
        101MP MUST NOT inherit 104MP packaging because the historical dims differ.
        """
        o = _orchestrator()
        size = '72x78 + 12"'

        # SABAQ has 104MP record (33×27×11, 1.3kg)
        evidence_104mp = _make_evidence(
            "ev-104mp", "TLS-MP-CB-DBF", size,
            packaging_l=33, packaging_b=27, packaging_h=11, packaging_w=1.3
        )

        # Draft proposes 101MP values (23×23×23, 3.0kg) but references 104MP evidence
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        draft.packaging_length_cm = DraftField(
            value=23, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        draft.packaging_breadth_cm = DraftField(
            value=23, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        draft.packaging_height_cm = DraftField(
            value=23, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )
        draft.packaging_weight_kg = DraftField(
            value=3.0, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-104mp"
        )

        # CEM verifies TLS-MP-RYB-DBF as Scenario B (it's a sibling family member)
        cem_result = {"exists": True, "active": True, "product_code": "TLS-MP-RYB-DBF"}

        o._evaluate_provenance_promotion(
            draft, [evidence_104mp], CatalogScenario.B,
            cem_verification_result=cem_result
        )

        # 101MP dims (23,23,23) don't match 104MP dims (33,27,11) → all must be rejected
        assert draft.packaging_length_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
            "101MP packaging_length (23) does not match 104MP (33) — must not be promoted"
        )
        assert draft.packaging_breadth_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
        assert draft.packaging_height_cm.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER
        assert draft.packaging_weight_kg.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER

    def test_101mp_evidence_matches_own_dims(self):
        """
        If SABAQ has a record for 101MP (23×23×23) and the draft proposes the same values,
        promotion is valid (product_code must match the candidate draft's CEM-verified pc).
        """
        o = _orchestrator()
        size = '72x78 + 12"'
        evidence_101mp = _make_evidence(
            "ev-101mp", "TLS-MP-RYB-DBF", size,
            packaging_l=23, packaging_b=23, packaging_h=23, packaging_w=3.0
        )
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        for attr, val in [
            ("packaging_length_cm", 23),
            ("packaging_breadth_cm", 23),
            ("packaging_height_cm", 23),
        ]:
            setattr(draft, attr, DraftField(
                value=val, provenance=FieldProvenance.AI_PROPOSED,
                candidate_sabaq_reference_id="ev-101mp"
            ))
        draft.packaging_weight_kg = DraftField(
            value=3.0, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-101mp"
        )

        cem_result = {"exists": True, "active": True, "product_code": "TLS-MP-RYB-DBF"}
        o._evaluate_provenance_promotion(
            draft, [evidence_101mp], CatalogScenario.B,
            cem_verification_result=cem_result
        )

        assert draft.packaging_length_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_breadth_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_height_cm.provenance == FieldProvenance.SABAQ_REUSED
        assert draft.packaging_weight_kg.provenance == FieldProvenance.SABAQ_REUSED

    def test_116bs_does_not_inherit_102bs_mrp(self):
        """
        Real data:
          102BS (KD-PINKGULBAHAR-KDB): MRP 2699
          116BS (KD-SSK-AQGB-KDB): MRP 1699

        MRP must NOT be promoted from 102BS to 116BS.
        No uniform_mrp_policy config exists — MRP is always UNKNOWN_REQUIRES_USER.
        """
        o = _orchestrator()
        size = "100*108 inches"
        evidence_102bs = _make_evidence(
            "ev-102bs", "KD-PINKGULBAHAR-KDB", size, mrp=2699
        )
        draft = CatalogDraft()
        draft.size = DraftField(value=size, provenance=FieldProvenance.AI_PROPOSED)
        draft.mrp = DraftField(
            value=2699, provenance=FieldProvenance.AI_PROPOSED,
            candidate_sabaq_reference_id="ev-102bs"
        )

        # CEM verifies KD-SSK-AQGB-KDB (116BS's family) as Scenario B
        cem_result = {"exists": True, "active": True, "product_code": "KD-SSK-AQGB-KDB"}
        o._evaluate_provenance_promotion(
            draft, [evidence_102bs], CatalogScenario.B,
            cem_verification_result=cem_result
        )

        assert draft.mrp.provenance == FieldProvenance.UNKNOWN_REQUIRES_USER, (
            "116BS MRP must not be inherited from 102BS — no uniform_mrp_policy exists"
        )
