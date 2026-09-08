"""
Claims ONE real, currently-eligible NDR queue item from the live production queue, runs it
through the exact real pipeline (evidence fetch -> mapping -> orchestrator -> CCC -> session
constants), and prints the complete payload that would be sent to Exotel - then stops.

Does NOT call register_engagement, prepare_engagement, or dispatch_provider_call. No phone
call is placed by this script under any circumstance.

Uses a distinct claimer_id so this claim is clearly identifiable in the database as a manual
inspection, separate from the live autonomous poller (which is also running locally and may
win the race for any given item - that's expected, not a bug in this script).

By explicit user decision: no synthetic/test data. This claims a REAL customer's NDR item, so
the printed output contains real customer PII (name, phone, address pincode, order/product
details, prior communication history). Treat the output accordingly.
"""
import asyncio
import json
import logging

logging.basicConfig(level=logging.WARNING)  # quiet the noisy libraries; we print explicitly
logger = logging.getLogger(__name__)

INSPECT_CLAIMER_ID = "brain_core_rabta_inspect"


async def inspect_one():
    from src.main import shopdeck_cem, ccc_builder, ndr_orch
    from src.workers.ndr_queue_poller import ShopdeckQueueEvidenceMapper
    from src.shared.requirement_classification_contracts import ClassifiedRequirement
    from src.shared.conversational_contracts import ConversationalUnderstanding, SemanticEntityReference
    from src.shared.evidence_request_contracts import AbstractEvidenceRequest, BusinessRealityStatus
    from src.api.webhooks.exotel_webhooks import build_session_constants

    print("Claiming one real eligible item from the live queue...")
    item = await shopdeck_cem.claim_ndr_work(INSPECT_CLAIMER_ID, lease_seconds=120)
    if not item:
        print("\nNo eligible item was available to claim (queue is empty, or the live "
              "autonomous poller already claimed whatever was there first - expected, not an error).")
        return

    queue_item_id = item["queue_item_id"]
    awb_no = item["awb_no"]
    print(f"\nClaimed queue_item_id={queue_item_id} awb_no={awb_no}")

    req = AbstractEvidenceRequest(
        classified_requirement=ClassifiedRequirement(
            understanding=ConversationalUnderstanding(
                original_query=f"Internal NDR Queue Fetch for AWB {awb_no}",
                parameters=[],
                entities=[SemanticEntityReference(inferred_type="ndr.entity.awb", original_expression=awb_no)],
            )
        )
    )
    evidence_res = await shopdeck_cem.execute_evidence_request(req)
    full_evidence = evidence_res.evidence_data if evidence_res.status == BusinessRealityStatus.EVIDENCE_AVAILABLE else {}

    trigger_evidence = ShopdeckQueueEvidenceMapper.map_to_evidence(item, full_evidence)
    decision = await ndr_orch.orchestrate_resolution(trigger_evidence)

    print(f"\nOrchestrator decision: should_dispatch={decision.should_dispatch} disposition={decision.disposition_code}")

    if not decision.should_dispatch:
        print("Orchestrator decided NOT to dispatch a call for this item - nothing further to inspect.")
        print("(Note: this claim will sit under claimer_id=brain_core_rabta_inspect until its "
              "120-second lease expires, at which point it becomes reclaimable normally again.)")
        return

    action = decision.action_request
    ccc = await ccc_builder.build(action)
    projection = ccc_builder.project(ccc)

    if not ccc.customer_profile.phone:
        print("No authoritative customer phone was hydrated - the real dispatch path would refuse to call here too.")
        return

    session_constants = build_session_constants(
        engagement_id="inspect_only_no_real_engagement",
        action_request_id=action.action_request_id,
        engagement={"call_context": projection.model_dump()},
    )

    print("\n" + "=" * 70)
    print("COMPLETE session_constants that would be sent to Exotel for this call:")
    print("=" * 70)
    print(json.dumps(session_constants, indent=2, ensure_ascii=False))
    print("=" * 70)
    print("\nSTOPPING HERE. No engagement was registered, no call was dispatched.")
    print("This claim will sit under claimer_id=brain_core_rabta_inspect until its 120-second "
          "lease expires, at which point it becomes normally reclaimable again - including by "
          "the live autonomous poller, which may then actually call this customer as intended.")


if __name__ == "__main__":
    asyncio.run(inspect_one())
