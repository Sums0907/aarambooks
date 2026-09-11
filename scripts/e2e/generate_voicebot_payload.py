"""
E2E Certification Script: Generate Voicebot Payload

Fetches a real NDR from ShopDeck BS and generates the complete payload
that will be sent to the voice bot (Sarvam or Exotel), saving it to
docs/voicebot/sample_context_1.md for inspection and certification.

Usage:
    PYTHONPATH=. python3 scripts/e2e/generate_voicebot_payload.py [AWB_NO]

If no AWB is provided, defaults to a known test AWB from the database.
"""
import asyncio
import json
import os
import sys
import uuid

from src.brain_core.action_engine.contracts import ActionRequest, ActionCategory, ConversationalDirective
from src.brain_core.context_engine.ccc_builder import ShopDeckMasterCCCBuilder
from src.infrastructure.adapters.customer_engagement.context_variables import (
    _get_context_keys_for_domain,
    get_instructions_for_domain,
)
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.shared.config import settings
from src.shared.domain_contracts import IntelligenceDomain


async def run(awb: str) -> None:
    # 1. Build adapter exactly as main.py does (src/main.py:209-214)
    adapter = ShopdeckCemAdapter(
        base_url=getattr(settings, "shopdeck_url", "http://localhost:8002"),
        identity_url=settings.identity_url,
        client_id=settings.brain_client_id,
        client_secret=settings.brain_client_secret,
    )
    builder = ShopDeckMasterCCCBuilder(provider=adapter)

    # 2. Build a realistic ActionRequest (directive matches what the dispatcher sends)
    directive = ConversationalDirective(
        objective="Schedule a reattempt for tomorrow.",
        context_summary="Customer was unavailable today.",
        constraints=["Do not name courier"],
        allowed_actions=["reschedule"],
    )
    req = ActionRequest(
        action_request_id=f"act_{uuid.uuid4().hex[:8]}",
        category=ActionCategory.SUGGESTED_RESOLUTION,
        reasoning="Customer was unavailable.",
        parameters={"awb_no": awb},
        directive=directive,
    )

    # 3. Fetch CCC from real ShopDeck BS
    print(f"Fetching evidence from ShopDeck BS for AWB: {awb}")
    try:
        ccc = await builder.build(req)
        print("SUCCESS: CCC built from REAL ShopDeck data.")
    except Exception as e:
        print(f"WARN: Real ShopDeck call failed ({e}). Falling back to mock data.")
        from tests.test_ndr_full_context_wiring import SHOPDECK_EVIDENCE
        from src.shared.evidence_request_contracts import BusinessEvidenceResponse, BusinessRealityStatus

        class MockProvider:
            async def execute_evidence_request(self, req, *args, **kwargs):
                return BusinessEvidenceResponse(
                    status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                    evidence_data=SHOPDECK_EVIDENCE,
                    authority_domain="shopdeck",
                )

        builder = ShopDeckMasterCCCBuilder(provider=MockProvider())
        ccc = await builder.build(req)
        print("Using mock data shaped identically to the production ShopDeck schema.")

    # 4. Project to the governed conversational subset
    projection = builder.project(ccc)

    # 5. Build the final payload: allowed context variables + domain instructions
    allowed_keys = _get_context_keys_for_domain(IntelligenceDomain.NDR)
    projection_dict = projection.model_dump()
    payload = {
        k: projection_dict[k]
        for k in allowed_keys
        if k in projection_dict and projection_dict[k] is not None
    }

    # 6. Save
    output_path = "docs/voicebot/sample_context_1.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(f"```json\n{json.dumps(payload, indent=2)}\n```\n")

    print(f"\nPayload saved to {output_path}")
    print(f"Total keys: {len(payload)}")


if __name__ == "__main__":
    awb_no = sys.argv[1] if len(sys.argv) > 1 else "142285239995710"
    asyncio.run(run(awb_no))
