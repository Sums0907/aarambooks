import uuid
import json
from typing import Optional
from uuid import UUID
from decimal import Decimal

import httpx

from src.shared.rabta_interfaces import ContextExecutionAdapter
from src.shared.evidence_request_contracts import (
    AbstractEvidenceRequest,
    BusinessEvidenceResponse,
    BusinessRealityStatus,
    BusinessStateVerificationRequest,
    BusinessStateVerificationResponse
)
from src.shared.conversational_contracts import ConversationalIntent
from src.application.catalog_contracts import (
    SaveProductFamilyPayload,
    SaveProductInput,
    SaveSkuInput,
    TransitionLifecycleStatePayload,
    MutationResponse,
)

class CatalogCemAdapter(ContextExecutionAdapter):
    """
    Physical execution adapter for Catalog BS.
    Implements the ContextExecutionAdapter boundary.
    - SEARCH: Queries the Catalog HTTP service for discovery.
    - ACTION: Executes SaveProductFamily mutation and handles SKU_COLLISION retries.

    Reaches Catalog only over HTTP (business_systems/catalog/api.py) - Catalog owns its own
    database connection end-to-end now. This adapter previously imported CatalogService and
    business_systems.catalog.models directly and opened its own asyncpg pool against
    `database_url` (Brain's own database, not Catalog's CATALOG_DATABASE_URL) - all the
    orchestration logic below (the collision-retry loop, the SaveProductFamily vs
    PrepareAndPublishShopDeck decision tree) is unchanged from that version; only the
    transport to Catalog changed from a direct method call to an HTTP request.
    """
    def __init__(self, base_url: str, internal_token: str, transport: Optional[httpx.AsyncBaseTransport] = None):
        self._base_url = base_url.rstrip("/")
        self._token = internal_token
        # transport is test-only: an httpx.ASGITransport lets tests exercise the real
        # FastAPI app + real database in-process, without a separate server, while
        # production always goes over a real network connection.
        self._transport = transport
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30.0,
                transport=self._transport,
            )
        return self._client

    async def verify_business_state(self, request: BusinessStateVerificationRequest) -> BusinessStateVerificationResponse:
        client = self._ensure_client()

        target = request.verification_target
        payload = request.context_payload

        if target == "product_code":
            code = payload.get("product_code")
            if not code:
                return BusinessStateVerificationResponse(is_verified=False, status=BusinessRealityStatus.EXECUTION_LIMITATION)

            resp = await client.post("/internal/verify/product-code", json={"product_code": code})
            resp.raise_for_status()
            data = resp.json()
            if not data["exists"]:
                return BusinessStateVerificationResponse(
                    is_verified=True,
                    status=BusinessRealityStatus.ENTITY_NOT_FOUND,
                    evidence_data=data,
                )
            return BusinessStateVerificationResponse(
                is_verified=True,
                status=BusinessRealityStatus.ENTITY_RESOLVED,
                evidence_data=data,
            )

        elif target == "family_existence":
            parent_id = payload.get("parent_internal_id")
            if not parent_id:
                return BusinessStateVerificationResponse(is_verified=False, status=BusinessRealityStatus.EXECUTION_LIMITATION)

            try:
                UUID(parent_id)
            except ValueError:
                return BusinessStateVerificationResponse(is_verified=False, status=BusinessRealityStatus.EXECUTION_LIMITATION)

            resp = await client.post("/internal/verify/family-existence", json={"parent_internal_id": parent_id})
            resp.raise_for_status()
            return BusinessStateVerificationResponse(
                is_verified=True,
                status=BusinessRealityStatus.ENTITY_RESOLVED,
                evidence_data=resp.json(),
            )

        return BusinessStateVerificationResponse(
            is_verified=False,
            status=BusinessRealityStatus.EXECUTION_LIMITATION,
            execution_limitations=[{"missing_parameter": "verification_target", "reason": f"Unsupported target: {target}"}]
        )

    async def execute_evidence_request(self, request: AbstractEvidenceRequest, auth_context: str) -> BusinessEvidenceResponse:
        understanding = request.classified_requirement.understanding
        intent = understanding.intent

        if intent == ConversationalIntent.SEARCH:
            return await self._handle_search(request)
        elif intent == ConversationalIntent.ACTION:
            return await self._handle_action(request)
        else:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[{"missing_parameter": "intent", "reason": f"Catalog CEM does not support intent: {intent}"}]
            )

    async def _handle_search(self, request: AbstractEvidenceRequest) -> BusinessEvidenceResponse:
        # Simple discovery by product_code alias for test coverage
        understanding = request.classified_requirement.understanding

        product_code = None
        for entity in understanding.entities:
            if entity.inferred_type == "product_code":
                product_code = entity.original_expression
                break

        if not product_code:
            return BusinessEvidenceResponse(status=BusinessRealityStatus.ENTITY_NOT_FOUND)

        client = self._ensure_client()
        resp = await client.get("/internal/search/product-by-code", params={"product_code": product_code})
        resp.raise_for_status()
        data = resp.json()
        records = data["results"]

        if len(records) == 0:
            return BusinessEvidenceResponse(status=BusinessRealityStatus.ENTITY_NOT_FOUND)
        elif len(records) == 1:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.ENTITY_RESOLVED,
                evidence_data={
                    "internal_id": records[0]["internal_id"],
                    "name": records[0]["name"]
                }
            )
        else:
            return BusinessEvidenceResponse(status=BusinessRealityStatus.MULTIPLE_CANDIDATES)

    async def _handle_action(self, request: AbstractEvidenceRequest) -> BusinessEvidenceResponse:
        understanding = request.classified_requirement.understanding
        params = {p.parameter_name: p.value for p in understanding.parameters} if understanding.parameters else {}

        operation = params.get("operation")
        if operation not in ("SaveProductFamily", "PrepareAndPublishShopDeck"):
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[{"missing_parameter": "operation", "reason": f"Catalog CEM does not support operation: {operation}"}]
            )

        # Parse the requested product and SKU
        product_code = params.get("product_code")
        parent_id = params.get("authorized_parent_internal_id")
        sku_candidates = params.get("sku_candidates", [])
        if isinstance(sku_candidates, str):
            try:
                # Handle single quotes if ast.literal_eval was used to generate it
                sku_candidates = json.loads(sku_candidates.replace("'", '"'))
            except:
                sku_candidates = [sku_candidates]

        color = params.get("colour", "Default")
        category = params.get("product_type", "GEN")

        if not sku_candidates:
            return BusinessEvidenceResponse(
                status=BusinessRealityStatus.EXECUTION_LIMITATION,
                execution_limitations=[{"missing_parameter": "sku_candidates", "reason": "No SKU candidates provided for mutation."}]
            )

        product_input = SaveProductInput(
            product_internal_id=UUID(parent_id) if parent_id else None,
            product_code=product_code or f"NEW-{uuid.uuid4().hex[:8].upper()}",
            name=params.get("product_name") or f"Product {category}",
            description=params.get("description"),
            product_type=category
        )

        client = self._ensure_client()

        # Bounded sequential execution loop across cognitive candidates
        for attempt, candidate_sku_id in enumerate(sku_candidates):
            try:
                sku_input = SaveSkuInput(
                    sku_id=candidate_sku_id,
                    colour=color,
                    mrp=Decimal(params["mrp"]) if "mrp" in params else None,
                    selling_price=Decimal(params["selling_price"]) if "selling_price" in params else None,
                    cost_price=Decimal(params["cost_price"]) if "cost_price" in params else None,
                    packaging_length_cm=Decimal(params["packaging_length_cm"]) if "packaging_length_cm" in params else None,
                    packaging_breadth_cm=Decimal(params["packaging_breadth_cm"]) if "packaging_breadth_cm" in params else None,
                    packaging_height_cm=Decimal(params["packaging_height_cm"]) if "packaging_height_cm" in params else None,
                    packaging_weight_kg=Decimal(params["packaging_weight_kg"]) if "packaging_weight_kg" in params else None,
                    sku_media_urls=params.get("sku_media_urls", [])
                )

                payload = SaveProductFamilyPayload(
                    product=product_input,
                    skus=[sku_input]
                )
            except Exception as e:
                # Catch Pydantic Validation errors for missing mandatory fields
                import pydantic
                if isinstance(e, pydantic.ValidationError):
                    missing = [{"missing_parameter": err["loc"][0], "reason": err["msg"]} for err in e.errors()]
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EXECUTION_LIMITATION,
                        execution_limitations=missing
                    )
                raise

            resp = await client.post(
                "/internal/products/save-family",
                json=payload.model_dump(mode="json"),
            )
            resp.raise_for_status()
            response = MutationResponse.model_validate(resp.json())

            if response.status == "SUCCESS":
                prod_id = response.product_internal_id

                # If macro-operation, proceed to transition and publish
                if operation == "PrepareAndPublishShopDeck":
                    trans_payload = TransitionLifecycleStatePayload(
                        product_internal_id=prod_id,
                        target_state="READY"
                    )
                    trans_resp = await client.post(
                        "/internal/products/transition",
                        json=trans_payload.model_dump(mode="json"),
                    )
                    trans_resp.raise_for_status()
                    trans_response = MutationResponse.model_validate(trans_resp.json())

                    if trans_response.status == "REJECTED":
                        # Surface missing fields back to orchestrator
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.EXECUTION_LIMITATION,
                            execution_limitations=[
                                {"missing_parameter": "validation", "reason": f"MISSING_MANDATORY_FIELD: {e.message}"}
                                for e in trans_response.errors
                            ]
                        )

                    # Transition succeeded, now publish
                    pub_resp = await client.post("/internal/publications/SHOPDECK")
                    pub_resp.raise_for_status()
                    pub_response = MutationResponse.model_validate(pub_resp.json())
                    if pub_response.status == "REJECTED":
                        return BusinessEvidenceResponse(
                            status=BusinessRealityStatus.EXECUTION_LIMITATION,
                            execution_limitations=[{"missing_parameter": "publish", "reason": f"Publication failed: {[e.message for e in pub_response.errors]}"}]
                        )

                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                        evidence_data={
                            "message": f"Successfully published Product Family with SKU {candidate_sku_id} to ShopDeck.",
                            "product_internal_id": str(prod_id),
                            "sku_id": candidate_sku_id,
                            "artifact_id": pub_response.response_metadata.get("artifact_id") if pub_response.response_metadata else None
                        }
                    )
                else:
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EVIDENCE_AVAILABLE,
                        evidence_data={
                            "message": f"Successfully saved Product Family with SKU {candidate_sku_id}",
                            "product_internal_id": str(prod_id),
                            "sku_id": candidate_sku_id
                        }
                    )
            elif response.status == "REJECTED":
                # Check for domain collision
                is_collision = any(e.error_code in ("SKU_COLLISION", "CROSS_PRODUCT_SKU_MUTATION_DENIED") for e in response.errors)
                if is_collision:
                    # Continue to next candidate
                    continue
                else:
                    # Non-retryable error
                    return BusinessEvidenceResponse(
                        status=BusinessRealityStatus.EXECUTION_LIMITATION,
                        execution_limitations=[{"missing_parameter": "validation", "reason": f"Validation failed: {[e.message for e in response.errors]}"}]
                    )

        # If the loop exhausts the candidates without returning SUCCESS
        return BusinessEvidenceResponse(
            status=BusinessRealityStatus.EXECUTION_LIMITATION,
            execution_limitations=[{"missing_parameter": "candidates", "reason": "SKU_PROPOSAL_EXHAUSTED"}]
        )
