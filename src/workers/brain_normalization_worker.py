import logging
import uuid
import pymongo
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import NormalizationStatus
from src.infrastructure.mongo_client import get_mongo_db
from src.brain_core.semantics.mapper import SemanticEvidenceMapper, SemanticEvidenceResult
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.shared.cognitive_planning_contracts import EvidencePackage, EvidenceItem, ProvenanceMetadata
from src.azm.interfaces import AzmProvider

logger = logging.getLogger(__name__)

class BrainNormalizationWorker:
    """
    Asynchronous Brain Normalization Worker.
    THIN orchestration layer:
    Events -> SemanticMapper -> NDRIntelligenceOrchestrator -> ndr_normalization_results.
    No ShopDeck DB access, no action execution, no semantic translation.
    """
    def __init__(
        self,
        engagement_repo: CustomerEngagementRepository,
        semantic_mapper: SemanticEvidenceMapper,
        ndr_orchestrator: NDRIntelligenceOrchestrator
    ):
        self.engagement_repo = engagement_repo
        self.semantic_mapper = semantic_mapper
        self.ndr_orchestrator = ndr_orchestrator
        self._db = None

    async def _get_db(self):
        if self._db is None:
            self._db = await get_mongo_db()
        return self._db

    async def run_one(self) -> bool:
        """
        Attempts to claim and process one pending normalization.
        Returns True if an engagement was processed, False if queue is empty.
        """
        # 1. ATOMIC CLAIM
        engagement = await self.engagement_repo.claim_pending_normalization()
        if not engagement:
            return False

        engagement_id = engagement["engagement_id"]
        normalization_version = engagement.get("normalization_version", 1)
        logger.info(f"Worker claimed engagement {engagement_id} for normalization.")

        started_at = datetime.now(UTC)

        try:
            # 2. EVIDENCE ASSEMBLY
            events = await self.engagement_repo.get_engagement_events(engagement_id)
            if not events:
                raise ValueError(f"No events found for engagement {engagement_id}")

            evidence_items = []
            unmapped_metadata = []
            
            # 3. SEMANTIC MAPPING
            for event in events:
                raw_payload = event.get("payload") or {}
                
                # Check for transcript inside Exotel webhook payload
                transcript_text = ""
                session_timestamp = None
                
                if "events" in raw_payload and isinstance(raw_payload["events"], list):
                    for sub_event in raw_payload["events"]:
                        if sub_event.get("event_type") == "transcript":
                            turns = sub_event.get("event_data") or sub_event.get("transcript") or []
                            for turn in turns:
                                content = turn.get("content", "")
                                role = turn.get("role", "unknown")
                                transcript_text += f"{role}: {content}\n"
                                
                                # Capture earliest timestamp
                                ts = turn.get("start_speech_timestamp")
                                if ts and not session_timestamp:
                                    session_timestamp = ts

                if not session_timestamp:
                    session_timestamp = str(event.get("occurred_at") or datetime.now(UTC).isoformat())
                    
                understanding = None
                if transcript_text:
                    from src.shared.conversational_contracts import MultimodalQuery
                    mq = MultimodalQuery(
                        text=transcript_text.strip(),
                        context_metadata={"session_timestamp": session_timestamp}
                    )
                    understanding = await self.ndr_orchestrator.extract_understanding(mq)

                provenance = {
                    "source_system": event.get("provider"),
                    "provider_event_id": event.get("provider_event_id"),
                    "event_type": event.get("event_type")
                }

                # Semantic Mapper strictly isolates raw -> canonical
                mapping_result: SemanticEvidenceResult = self.semantic_mapper.map_evidence(raw_payload, provenance)
                
                unmapped_metadata.append(mapping_result.unmapped_physical)

                data_payload = mapping_result.mapped_canonical
                
                # Inject extracted conversational attributes
                if transcript_text:
                    data_payload["raw_transcript"] = transcript_text.strip()
                    if understanding and hasattr(understanding, "attributes"):
                        for attr in understanding.attributes:
                            data_payload[attr.attribute_name] = attr.original_expression

                # Hydrate the canonical entity identity from the engagement context
                if "ndr.entity.awb" not in data_payload and engagement.get("awb_no"):
                    data_payload["ndr.entity.awb"] = engagement["awb_no"]

                evidence_items.append(EvidenceItem(
                    item_id=str(event.get("provider_event_id") or uuid.uuid4()),
                    semantic_identity="ndr.event_payload",
                    data_payload=data_payload,
                    provenance=ProvenanceMetadata(
                        source_system=event.get("provider") or "unknown",
                        retrieval_timestamp=event.get("occurred_at") or datetime.now(UTC)
                    )
                ))
            
            # Ensure we preserve mapping metadata for the persistence layer
            mapping_metadata = {
                "unmapped": unmapped_metadata
            }

            evidence_pkg = EvidencePackage(
                package_id=str(uuid.uuid4()),
                plan_id=str(uuid.uuid4()),
                sufficiency_assessment="SUFFICIENT",
                evidence_items=evidence_items
            )

            # 4. NDR BRAIN INTERFACE
            decision, action, message = await self.ndr_orchestrator.orchestrate_resolution(evidence_pkg)

            # 5. NORMALIZATION RESULT
            db = await self._get_db()
            
            # Extract target identity from canonical evidence
            target_identity = "UNKNOWN"
            for item in evidence_items:
                if item.data_payload and "ndr.entity.awb" in item.data_payload:
                    target_identity = item.data_payload["ndr.entity.awb"]
                    break

            # Idempotency constraint check (Upsert based on engagement_id and normalization_version)
            result_doc = {
                "normalization_id": str(uuid.uuid4()),
                "engagement_id": engagement_id,
                "normalization_version": normalization_version,
                "action_request_id": str(uuid.uuid4()),
                "brain_decision_id": str(uuid.uuid4()),
                "target_identity": target_identity,
                "recommendation": decision.recommended_alternative_id,
                "authorized_action": action.category.value if action else "NONE",
                "action_parameters": action.parameters if action else {},
                "reasoning": action.reasoning if action else "",
                "diagnosis": "NOT_AVAILABLE",
                "risk_score": "NOT_AVAILABLE",
                "source_event_ids": [str(e.get("provider_event_id")) for e in events],
                "semantic_mapping_metadata": mapping_metadata,
                "provenance": "worker",
                "normalization_status": NormalizationStatus.COMPLETED.value,
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
                "created_at": datetime.now(UTC)
            }
            
            try:
                await db.ndr_normalization_results.insert_one(result_doc)
            except pymongo.errors.DuplicateKeyError:
                # 7. IDEMPOTENCY
                logger.info(f"Normalization already completed for {engagement_id} v{normalization_version}. Idempotent no-op.")
            
            # 6. NORMALIZATION STATE (Success)
            await self.engagement_repo.update_normalization_status(engagement_id, NormalizationStatus.COMPLETED)
            logger.info(f"Normalization COMPLETED for {engagement_id}")
            return True

        except Exception as e:
            # 9. FAILURE HANDLING
            # In a real system, distinguish retryable (network) vs fatal (ValueError, KeyError, strict semantic mismatch)
            is_fatal = isinstance(e, (ValueError, TypeError, KeyError))
            status = NormalizationStatus.FAILED if is_fatal else NormalizationStatus.RETRY_PENDING
            await self.engagement_repo.update_normalization_status(engagement_id, status)
            logger.error(f"Normalization {status.name} for {engagement_id}: {str(e)}")
            return True

