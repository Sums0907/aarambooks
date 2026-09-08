import httpx
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from src.shared.rabta_interfaces import ContextExecutionAdapter
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    BusinessStateVerificationRequest,
    BusinessStateVerificationResponse,
    ExecutionLimitation
)

logger = logging.getLogger(__name__)

# ── M2M Token Cache (simple in-process cache) ─────────────────────────────────
_cached_token: Optional[str] = None

async def _get_shopdeck_token(identity_url: str, client_id: str, client_secret: str) -> Optional[str]:
    """Fetches a fresh M2M token from the Aaram Identity server."""
    global _cached_token
    if _cached_token:
        return _cached_token
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{identity_url}/auth/service-token",
                json={"client_id": client_id, "client_secret": client_secret}
            )
            if resp.status_code == 200:
                _cached_token = resp.json().get("access_token")
                return _cached_token
            else:
                logger.error(f"ShopdeckCemAdapter: Identity token fetch failed {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.error(f"ShopdeckCemAdapter: Identity token fetch error: {e}")
    return None


class ShopdeckCemAdapter(ContextExecutionAdapter):
    """
    Sovereign ShopDeck runtime boundary.
    Executes AbstractEvidenceRequests against the ShopDeck BS HTTP API.
    Authenticates via the Aaram Identity M2M service-token endpoint.
    """
    def __init__(
        self,
        base_url: str,
        identity_url: str = "http://localhost:9000",
        client_id: str = "aaram_brain",
        client_secret: str = "Samashu@01"
    ):
        self.base_url = base_url
        self.identity_url = identity_url
        self.client_id = client_id
        self.client_secret = client_secret

    async def _get_auth_header(self) -> dict:
        token = await _get_shopdeck_token(self.identity_url, self.client_id, self.client_secret)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def _authed_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Sends one HTTP request with the cached M2M bearer token, refreshing it once on a 401.

        The M2M token cache (_cached_token, module-level) never expires proactively - only
        execute_evidence_request (the read path) previously handled a stale token, by clearing
        the cache and retrying. claim_ndr_work, register_engagement, update_queue_status, and
        submit_intelligence - the entire write surface - had no such handling: in a long-running
        process, a token that goes stale mid-session would fail every subsequent write with an
        unhandled 401 until the process restarted. Centralizing the retry here means every
        caller gets it, including future ones, without re-deriving this logic per method.
        """
        global _cached_token
        headers = kwargs.pop("headers", {}) or {}
        # Dispatch via the method-named call (client.post/.patch/.get), not client.request(...) -
        # existing tests patch httpx.AsyncClient.post/.patch directly (a common, simple mock
        # style already used throughout this codebase's test suite), and that patch does not
        # intercept client.request() even for the same HTTP verb.
        async with httpx.AsyncClient(timeout=10.0) as client:
            call = getattr(client, method.lower())
            resp = await call(url, headers={**headers, **(await self._get_auth_header())}, **kwargs)
            if resp.status_code == 401:
                _cached_token = None
                resp = await call(url, headers={**headers, **(await self._get_auth_header())}, **kwargs)
            return resp

    async def invoke_capability(self, capability_urn: str, requirement: Any, authorization_context: str) -> Any:
        from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
        from src.shared.evidence_request_contracts import AbstractEvidenceRequest
        
        awb_no = None
        for constraint in requirement.semantic_constraints:
            if constraint.identity == "ndr.entity.awb":
                awb_no = constraint.bound_value
                
        if not awb_no:
            # Fallback parsing description
            import re
            m = re.search(r"awb\s+(\d+)", requirement.original_requirement.semantic_description, re.IGNORECASE)
            if m:
                awb_no = m.group(1)

        from types import SimpleNamespace
        class DummyReq:
            def __init__(self):
                self.classified_requirement = SimpleNamespace(
                    requirement_id=requirement.requirement_id,
                    understanding=SimpleNamespace(
                        parameters=[SimpleNamespace(parameter_name="awb", value=awb_no)],
                        entities=None,
                        original_query=requirement.original_requirement.semantic_description
                    )
                )

        from src.shared.evidence_request_contracts import BusinessRealityStatus
        from src.shared.context_contracts.provider import ContextRetrievalStatus, ContextCapabilityResult
        from src.shared.cognitive_planning_contracts import ProvenanceMetadata
        from datetime import datetime, UTC
        
        try:
            res = await self.execute_evidence_request(DummyReq(), authorization_context)
            
            print(f"DEBUG SHOPDECK RES STATUS: {res.status}", flush=True)
            if res.execution_limitations:
                print(f"DEBUG SHOPDECK LIMITATIONS: {res.execution_limitations}", flush=True)
                
            status = ContextRetrievalStatus.SUCCESS
            if res.status == BusinessRealityStatus.ENTITY_NOT_FOUND or res.status == BusinessRealityStatus.EVIDENCE_UNAVAILABLE:
                status = ContextRetrievalStatus.DATA_UNAVAILABLE
            elif res.status == BusinessRealityStatus.EXECUTION_LIMITATION:
                status = ContextRetrievalStatus.ERROR

            return ContextCapabilityResult(
                status=status,
                data=res.evidence_data,
                provenance_metadata=ProvenanceMetadata(
                    source_system="urn:aarambooks:shopdeck:bs",
                    retrieval_timestamp=datetime.now(UTC)
                )
            )
        except Exception as e:
            print(f"DEBUG SHOPDECK EXCEPTION in invoke_capability: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return ContextCapabilityResult(
                status=ContextRetrievalStatus.ERROR,
                data=None,
                provenance_metadata=ProvenanceMetadata(
                    source_system="urn:aarambooks:shopdeck:bs",
                    retrieval_timestamp=datetime.now(UTC),
                    derivation_metadata=str(e)
                )
            )

    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str = "") -> BusinessEvidenceResponse:
        print(f"DEBUG SHOPDECK CEM EXECUTING for search query {request.classified_requirement.understanding.original_query}")
        understanding = request.classified_requirement.understanding
        params = {p.parameter_name: p.value for p in understanding.parameters} if understanding.parameters else {}

        awb_no = params.get("awb") or params.get("tracking_number") or params.get("awb_no")

        if not awb_no and understanding.entities:
            for entity in understanding.entities:
                if getattr(entity, "inferred_type", None) == "ndr.entity.awb":
                    awb_no = entity.original_expression
                    break

        if not awb_no:
            import re
            awb_match = re.search(r'\b([A-Z0-9]{8,16})\b', understanding.original_query, re.IGNORECASE)
            if awb_match:
                awb_no = awb_match.group(1)

        if not awb_no:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[ExecutionLimitation(missing_parameter="awb_no", reason="No AWB provided for NDR retrieval.")]
            )

        # Correct ShopDeck NDR endpoint
        url = urljoin(self.base_url, f"/api/v1/ndr/{awb_no}")
        headers = await self._get_auth_header()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    # customer_number is now returned by the ShopDeck BS API directly (via customer_info JOIN).
                    # Brain never accesses ShopDeck DB directly.
                    customer_number = data.get("customer_number")
                    if customer_number:
                        data["customer.attribute.phone"] = customer_number

                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                        evidence_data=data
                    )
                elif response.status_code == 401:
                    # Token may have expired — clear cache and retry once
                    global _cached_token
                    _cached_token = None
                    headers = await self._get_auth_header()
                    async with httpx.AsyncClient(timeout=10.0) as retry_client:
                        response = await retry_client.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        # customer_number is returned by the ShopDeck BS API directly.
                        # Brain never accesses ShopDeck DB directly.
                        customer_number = data.get("customer_number")
                        if customer_number:
                            data["customer.attribute.phone"] = customer_number

                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                            evidence_data=data
                        )
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EXECUTION_LIMITATION,
                        execution_limitations=[ExecutionLimitation(missing_parameter="auth", reason=f"ShopDeck auth failed after token refresh. HTTP {response.status_code}")]
                    )
                elif response.status_code == 404:
                    detail = response.json().get('detail', '')
                    if detail == 'AWB_NOT_FOUND':
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.ENTITY_NOT_FOUND,
                            execution_limitations=[ExecutionLimitation(missing_parameter="awb", reason="AWB genuinely does not exist.")]
                        )
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                        execution_limitations=[ExecutionLimitation(missing_parameter="data", reason=f"No NDR records found for AWB: {detail}")]
                    )
                elif response.status_code == 503:
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_UNAVAILABLE,
                        execution_limitations=[ExecutionLimitation(missing_parameter="data", reason="ShopDeck NDR data unavailable — backfill incomplete.")]
                    )
                else:
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EXECUTION_LIMITATION,
                        execution_limitations=[ExecutionLimitation(missing_parameter="api", reason=f"ShopDeck API returned HTTP {response.status_code}")]
                    )

        except httpx.RequestError as e:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[ExecutionLimitation(missing_parameter="network", reason=f"ShopDeck API network error: {str(e)}")]
            )
        except Exception as e:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[ExecutionLimitation(missing_parameter="system", reason=f"ShopDeck API unexpected error: {str(e)}")]
            )

    async def verify_business_state(self, request: BusinessStateVerificationRequest) -> BusinessStateVerificationResponse:
        return BusinessStateVerificationResponse(
            is_verified=False,
            status=BusinessRealityStatus.EXECUTION_LIMITATION,
            execution_limitations=[ExecutionLimitation(missing_parameter="endpoint", reason="ShopDeck CEM does not support state verification yet.")]
        )

    # ---------------------------------------------------------
    # NDR QUEUE ENDPOINTS
    # ---------------------------------------------------------
    async def claim_ndr_work(self, claimer_id: str, lease_seconds: int = 300) -> Optional[Dict[str, Any]]:
        url = urljoin(self.base_url, "/api/v1/ndr/queue/claim")
        payload = {"claimer_id": claimer_id, "lease_seconds": lease_seconds}
        resp = await self._authed_request("POST", url, json=payload)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 204:
            return None
        else:
            print(resp.text); resp.raise_for_status()

    async def register_engagement(self, queue_item_id: str, engagement_id: str, idempotency_key: str) -> Dict[str, Any]:
        url = urljoin(self.base_url, "/api/v1/ndr/engagements")
        payload = {
            "queue_item_id": queue_item_id,
            "engagement_id": engagement_id,
            "idempotency_key": idempotency_key
        }
        resp = await self._authed_request("POST", url, json=payload)
        print(resp.text); resp.raise_for_status()
        return resp.json()

    async def update_queue_status(self, queue_item_id: str, status: str, engagement_id: Optional[str] = None, **extra) -> Dict[str, Any]:
        url = urljoin(self.base_url, f"/api/v1/ndr/queue/{queue_item_id}/status")
        payload = {"status": status}
        if engagement_id:
            payload["engagement_id"] = engagement_id
        payload.update(extra)
        resp = await self._authed_request("PATCH", url, json=payload)
        print(resp.text); resp.raise_for_status()
        return resp.json()

    async def submit_intelligence(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = urljoin(self.base_url, "/api/v1/ndr/intelligence_results")
        resp = await self._authed_request("POST", url, json=payload)
        print(resp.text); resp.raise_for_status()
        return resp.json()


class ShopdeckQueueEvidenceMapper:
    """
    Maps ShopDeck BS's real NDRShipmentContext schema (see
    business_systems/shopdeck/backend/api/schemas/ndr.py) into the EvidencePackage the
    NDR orchestrator consumes. Every mapping below was checked against that schema
    directly - it has no field literally named "status" (only the separate order_status
    and ndr_status), and no "customer.attribute.phone" (only customer_number). Both were
    silently returning None in production before this fix.
    """

    @staticmethod
    def map_to_evidence(queue_item: dict, full_evidence: dict) -> 'EvidencePackage':
        from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata

        payload = {}
        # Combine queue item facts and full evidence facts
        payload["ndr.entity.awb"] = queue_item.get("awb_no")
        payload["shopdeck.event.delivery_exception.reason"] = queue_item.get("ndr_reason_at_enroll")

        # ndr_attempt_seq is the enrollment-time snapshot ShopDeck froze into ndr_queue
        # (see enroll_eligible_ndrs() in ndr_queue_repository.py: both ndr_attempt_seq and
        # ndr_count_at_enroll are populated from the SAME snr.ndr_count value at insert
        # time - they are synonyms, not two different concepts). Preserved here as a
        # separate audit-trail field. It is NOT used as the live attempt count below,
        # since it can go stale if another delivery attempt happens while this item sits
        # in the queue; shopdeck.metric.ndr_count (from the live evidence fetch) is used
        # for that instead. Not proven identical in every case - kept distinct on purpose.
        if queue_item.get("ndr_attempt_seq") is not None:
            payload["shopdeck.queue.ndr_attempt_seq_at_enroll"] = queue_item.get("ndr_attempt_seq")

        if full_evidence:
            payload["ndr.vocabulary.ndr_status"] = full_evidence.get("ndr_status")
            payload["shopdeck.metric.order_status"] = full_evidence.get("order_status")
            payload["ndr.entity.courier_partner"] = full_evidence.get("courier_partner")
            payload["shopdeck.metric.ndr_count"] = full_evidence.get("ndr_count")
            payload["shopdeck.entity.payment.mode"] = full_evidence.get("payment_mode")
            # Collectable amount stays collectable - never substituted for gross order value.
            payload["shopdeck.entity.order.collectable_amount"] = full_evidence.get("cod_amount")
            # Real gross order value: sum of line-item selling_price * quantity, when items
            # are present. Falls back to None (never to cod_amount, which is 0 for prepaid
            # orders and would misrepresent a real order as worthless).
            items = full_evidence.get("items") or []
            if items:
                gross_value = sum(
                    float(it.get("selling_price") or 0.0) * int(it.get("quantity") or 0)
                    for it in items
                )
                payload["shopdeck.entity.order.gross_value"] = gross_value
            payload["customer.attribute.phone"] = full_evidence.get("customer_number")
            payload["ndr.entity.customer"] = full_evidence.get("customer_name")
            payload["ndr.entity.customer_id"] = full_evidence.get("customer_id")
            payload["ndr.entity.order_id"] = full_evidence.get("order_id")
            # Delivery destination pincode - the parcel has already reached this pincode's
            # courier distribution point, so any customer-stated address change is only
            # actionable if it stays within this exact pincode. See
            # NDRShipmentContext.drop_pincode in business_systems/shopdeck's ndr schema.
            payload["ndr.entity.destination_pincode"] = full_evidence.get("drop_pincode")

            if "allowable_reattempt_dates" in full_evidence:
                payload["shopdeck.policy.allowable_reattempt_dates"] = full_evidence["allowable_reattempt_dates"]

        from datetime import datetime, UTC
        import uuid
        return EvidencePackage(
            package_id=f"pkg_{uuid.uuid4().hex[:8]}",
            plan_id="plan_ndr",
            sufficiency_assessment="Sufficient evidence acquired from Shopdeck BS",
            evidence_items=[
                EvidenceItem(
                    item_id=str(uuid.uuid4()),
                    semantic_identity="shopdeck_bs_ndr",
                    data_payload=payload,
                    provenance=ProvenanceMetadata(source_system="urn:aarambooks:shopdeck:bs", retrieval_timestamp=datetime.now(UTC))
                )
            ]
        )

