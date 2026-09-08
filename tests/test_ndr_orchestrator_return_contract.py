"""
Regression coverage for a confirmed blocker found during the Gate 3 pre-flight audit:
NDRIntelligenceOrchestrator.orchestrate_resolution() returned a 3-tuple on its early-exit
paths (AWB missing, NDR already closed) but a bare DispatchDecision on the normal path.
The poller (src/workers/ndr_queue_poller.py) always does `decision.should_dispatch`
immediately after calling this method - a 3-tuple has no such attribute, so the closed-NDR
path crashed with AttributeError on every real occurrence, not just intermittently.

These tests call the REAL orchestrator directly (no mocking of orchestrate_resolution
itself) so a regression back to the tuple-returning behavior fails here, not silently.
Only the memory provider is stubbed, since orchestrate_resolution's control flow never
touches the gateway or knowledge providers - stubbing memory does not hide the bug this
file exists to catch.
"""
import sys
from unittest.mock import AsyncMock, MagicMock
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['pymongo.errors'] = MagicMock()

import uuid
from datetime import datetime, UTC

import pytest

from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.intelligence_domains.ndr.models import DispatchDecision, DispatchDisposition
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata


def _evidence(payload: dict) -> EvidencePackage:
    return EvidencePackage(
        package_id=f"pkg_{uuid.uuid4().hex[:8]}",
        plan_id="plan_ndr",
        sufficiency_assessment="test",
        evidence_items=[
            EvidenceItem(
                item_id=str(uuid.uuid4()),
                semantic_identity="shopdeck_bs_ndr",
                data_payload=payload,
                provenance=ProvenanceMetadata(source_system="urn:test", retrieval_timestamp=datetime.now(UTC)),
            )
        ],
    )


def _orchestrator() -> NDRIntelligenceOrchestrator:
    return NDRIntelligenceOrchestrator(
        gateway=AsyncMock(),
        knowledge=AsyncMock(),
        memory=AsyncMock(),
    )


ACTIVE_NDR_PAYLOAD = {
    "ndr.entity.awb": "AWB123",
    "ndr.vocabulary.ndr_status": "pending",
    "shopdeck.metric.order_status": "dispatched",
    "ndr.entity.courier_partner": "Delhivery",
    "shopdeck.metric.ndr_count": 1,
    "shopdeck.event.delivery_exception.reason": "Customer unavailable",
    "shopdeck.entity.payment.mode": "cod",
}


@pytest.mark.asyncio
async def test_normal_dispatch_returns_bare_dispatch_decision():
    decision = await _orchestrator().orchestrate_resolution(_evidence(ACTIVE_NDR_PAYLOAD))
    assert isinstance(decision, DispatchDecision)
    assert decision.should_dispatch is True
    assert decision.disposition_code == DispatchDisposition.ENGAGE
    assert decision.action_request is not None


@pytest.mark.asyncio
async def test_awb_missing_returns_bare_dispatch_decision_not_a_tuple():
    decision = await _orchestrator().orchestrate_resolution(_evidence({}))
    assert isinstance(decision, DispatchDecision), f"expected DispatchDecision, got {type(decision)}"
    assert decision.should_dispatch is False
    # Must not raise AttributeError - this is the exact crash the audit found.
    assert decision.should_dispatch is False


@pytest.mark.asyncio
async def test_already_closed_ndr_returns_bare_dispatch_decision_not_a_tuple():
    closed_payload = dict(ACTIVE_NDR_PAYLOAD)
    closed_payload["ndr.vocabulary.ndr_status"] = "delivered"
    decision = await _orchestrator().orchestrate_resolution(_evidence(closed_payload))
    assert isinstance(decision, DispatchDecision), f"expected DispatchDecision, got {type(decision)}"
    assert decision.should_dispatch is False
    assert decision.disposition_code == DispatchDisposition.ALREADY_RESOLVED
    assert decision.action_request is None


@pytest.mark.asyncio
async def test_intelligence_pipeline_failure_returns_explicit_disposition(monkeypatch):
    from src.intelligence_domains.ndr.knowledge import NDRDiagnosticEngine

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated knowledge engine failure")

    monkeypatch.setattr(NDRDiagnosticEngine, "diagnose_failure", staticmethod(_boom))

    decision = await _orchestrator().orchestrate_resolution(_evidence(ACTIVE_NDR_PAYLOAD))
    assert isinstance(decision, DispatchDecision)
    assert decision.should_dispatch is False
    assert decision.disposition_code == DispatchDisposition.INTELLIGENCE_FAILURE
    assert decision.action_request is None


def test_dispatch_decision_rejects_should_dispatch_true_without_action_request():
    with pytest.raises(Exception):
        DispatchDecision(should_dispatch=True, disposition_code=DispatchDisposition.ENGAGE, action_request=None)


def test_dispatch_decision_rejects_action_request_when_not_dispatching():
    from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ConversationalDirective
    directive = ConversationalDirective(objective="x", context_summary="y", allowed_actions=[], constraints=[])
    action = ActionRequest(
        action_request_id="a1",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="x",
        parameters={},
        directive=directive,
    )
    with pytest.raises(Exception):
        DispatchDecision(should_dispatch=False, disposition_code=DispatchDisposition.ALREADY_RESOLVED, action_request=action)
