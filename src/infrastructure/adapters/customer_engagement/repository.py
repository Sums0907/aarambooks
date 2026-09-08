from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
import logging
import pymongo
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)
import logging

from src.infrastructure.mongo_client import get_mongo_db
from src.infrastructure.adapters.customer_engagement.models import (
    CustomerEngagementRecord,
    CustomerEngagementEvent,
    EngagementState,
    NormalizationStatus
)

class CustomerEngagementRepository:
    def __init__(self):
        self._db = None

    async def _get_db(self):
        if self._db is None:
            self._db = await get_mongo_db()
        return self._db

    async def setup_indexes(self):
        db = await self._get_db()
        engagements = db.customer_engagements
        events = db.customer_engagement_events

        # Engagements Indexes
        await engagements.create_index("engagement_id", unique=True)
        await engagements.create_index("action_request_id")
        await engagements.create_index([("provider", pymongo.ASCENDING), ("provider_call_id", pymongo.ASCENDING)])
        await engagements.create_index([("provider", pymongo.ASCENDING), ("provider_session_id", pymongo.ASCENDING)])
        await engagements.create_index("status")
        await engagements.create_index("normalization_status")

        # Events Indexes
        # Sparse unique index on provider_event_id so nulls don't trigger duplicate key errors
        await events.create_index(
            [("provider", pymongo.ASCENDING), ("provider_event_id", pymongo.ASCENDING)],
            unique=True,
            sparse=True 
        )
        await events.create_index("occurred_at")
        await events.create_index("engagement_id")
        await events.create_index("provider_session_id")

    async def create_engagement(self, record: CustomerEngagementRecord) -> CustomerEngagementRecord:
        db = await self._get_db()
        doc = record.model_dump()
        doc["normalization_status"] = NormalizationStatus.NOT_READY
        doc["created_at"] = datetime.now(UTC)
        doc["updated_at"] = doc["created_at"]
        
        try:
            await db.customer_engagements.insert_one(doc)
            return record
        except DuplicateKeyError:
            existing = await db.customer_engagements.find_one({"engagement_id": record.engagement_id})
            if existing:
                if existing.get("action_request_id") == record.action_request_id:
                    # Idempotent retry, safe to return existing
                    return CustomerEngagementRecord(**existing)
                else:
                    raise ValueError(f"Engagement ID {record.engagement_id} already exists for a different action request.")
            raise

    async def get_engagement(self, engagement_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        return await db.customer_engagements.find_one({"engagement_id": engagement_id})

    async def get_engagement_by_provider_correlation(
        self, provider: str, call_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        query = {"provider": provider}
        
        conditions = []
        if call_id:
            conditions.append({"provider_call_id": call_id})
        if session_id:
            conditions.append({"provider_session_id": session_id})
            
        if not conditions:
            return None
            
        query["$or"] = conditions
        return await db.customer_engagements.find_one(query)

    async def update_engagement_correlation(
        self, engagement_id: str, call_id: Optional[str] = None, session_id: Optional[str] = None, conversation_id: Optional[str] = None
    ) -> bool:
        db = await self._get_db()
        update_fields = {"updated_at": datetime.now(UTC)}
        if call_id: update_fields["provider_call_id"] = call_id
        if session_id: update_fields["provider_session_id"] = session_id
        if conversation_id: update_fields["provider_conversation_id"] = conversation_id
        
        if len(update_fields) == 1:
            return True
            
        res = await db.customer_engagements.update_one(
            {"engagement_id": engagement_id},
            {"$set": update_fields}
        )
        
        # Retroactively link any out-of-order orphaned events that arrived before correlation was known
        if session_id:
            await db.customer_engagement_events.update_many(
                {"provider_session_id": session_id, "engagement_id": None},
                {"$set": {"engagement_id": engagement_id}}
            )
            
        return res.modified_count > 0

    async def transition_state(self, engagement_id: str, new_state: EngagementState) -> bool:
        """
        Atomic state transition preventing out-of-order regression.
        Permitted transitions:
        REQUESTED -> DISPATCHED, FAILED
        DISPATCHED -> CONNECTED, FAILED
        CONNECTED -> IN_PROGRESS, COMPLETED, FAILED, ESCALATED
        IN_PROGRESS -> COMPLETED, FAILED, ESCALATED
        """
        db = await self._get_db()
        
        allowed_previous_states = []
        if new_state == EngagementState.DISPATCHED:
            allowed_previous_states = [EngagementState.REQUESTED]
        elif new_state == EngagementState.CONNECTED:
            allowed_previous_states = [EngagementState.REQUESTED, EngagementState.DISPATCHED]
        elif new_state == EngagementState.IN_PROGRESS:
            allowed_previous_states = [EngagementState.REQUESTED, EngagementState.DISPATCHED, EngagementState.CONNECTED]
        elif new_state in (EngagementState.COMPLETED, EngagementState.FAILED, EngagementState.ESCALATED):
            # Terminal states can be reached from anywhere except other terminal states
            allowed_previous_states = [
                EngagementState.REQUESTED, EngagementState.DISPATCHED, 
                EngagementState.CONNECTED, EngagementState.IN_PROGRESS
            ]
        elif new_state == EngagementState.REQUESTED:
            return False # Cannot transition backwards
            
        update_set = {
            "status": new_state,
            "updated_at": datetime.now(UTC)
        }
        
        # If transitioning to a terminal state, queue for normalization
        if new_state in (EngagementState.COMPLETED, EngagementState.FAILED, EngagementState.ESCALATED):
            update_set["normalization_status"] = NormalizationStatus.PENDING
            
        # Compare and swap using allowed previous states
        res = await db.customer_engagements.update_one(
            {
                "engagement_id": engagement_id, 
                "status": {"$in": allowed_previous_states}
            },
            {
                "$set": update_set
            }
        )
        
        # True if transition happened, False if ignored (e.g. out of order or already terminal)
        return res.modified_count > 0

    async def log_event(self, event: CustomerEngagementEvent) -> bool:
        """
        Idempotent event logging. Returns True if inserted, False if duplicated.
        """
        db = await self._get_db()
        doc = event.model_dump()
        doc["received_at"] = datetime.now(UTC)
        
        try:
            await db.customer_engagement_events.insert_one(doc)
            return True
        except DuplicateKeyError:
            # Duplicate webhook delivery - safe no-op
            logger.info(f"Duplicate event {event.provider_event_id} safely ignored.")
            return False

    async def claim_pending_normalization(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claims a terminal engagement for normalization.
        """
        db = await self._get_db()
        return await db.customer_engagements.find_one_and_update(
            {
                "status": {"$in": [EngagementState.COMPLETED, EngagementState.FAILED, EngagementState.ESCALATED]},
                "normalization_status": NormalizationStatus.PENDING
            },
            {
                "$set": {
                    "normalization_status": NormalizationStatus.PROCESSING,
                    "updated_at": datetime.now(UTC)
                }
            },
            return_document=pymongo.ReturnDocument.AFTER
        )
        
    async def get_engagement_events(self, engagement_id: str) -> List[Dict[str, Any]]:
        """
        Loads all events for an engagement, deterministically ordered.
        """
        db = await self._get_db()
        cursor = db.customer_engagement_events.find({"engagement_id": engagement_id})
        # Sort by occurred_at ASC, sequence ASC (if present), provider_event_id ASC
        cursor.sort([
            ("occurred_at", pymongo.ASCENDING),
            ("sequence", pymongo.ASCENDING),
            ("provider_event_id", pymongo.ASCENDING)
        ])
        return await cursor.to_list(length=None)

    async def update_normalization_status(self, engagement_id: str, status: NormalizationStatus) -> bool:
        """
        Updates the normalization status of an engagement.
        """
        db = await self._get_db()
        res = await db.customer_engagements.update_one(
            {"engagement_id": engagement_id},
            {"$set": {"normalization_status": status, "updated_at": datetime.now(UTC)}}
        )
        return res.modified_count > 0

    async def record_pending_ndr_outcome(self, engagement_id: str, data: Dict[str, Any]) -> bool:
        """
        Overwrites the "current best" NDR outcome for this engagement with every decisive
        transcript turn - unconditionally, so it always reflects the LATEST decisive turn, not
        the first. Deliberate design choice: a customer can change their mind mid-call (e.g.
        first ask for a date the bot can't offer, then settle for the one it can), and the
        outcome ShopDeck should see is what they ended on, not what they said first.

        This does NOT talk to ShopDeck - it only updates local bookkeeping. The actual
        one-time submission happens at session-end (see claim_intelligence_writeback below),
        reading back whatever this last wrote. Ambiguous (UNCLEAR) turns must never call this -
        callers should skip it so an ambiguous turn doesn't overwrite a real prior answer.
        """
        db = await self._get_db()
        res = await db.customer_engagements.update_one(
            {"engagement_id": engagement_id},
            {"$set": {"metadata.pending_ndr_outcome": data, "updated_at": datetime.now(UTC)}},
        )
        return res.modified_count > 0

    async def claim_intelligence_writeback(self, engagement_id: str, result_id: str) -> bool:
        """
        Atomic compare-and-swap claiming the right to submit an NDR intelligence result for
        this engagement, exactly once.

        ShopDeck's persist_intelligence_atomic (business_systems/shopdeck/backend/api/
        repositories/ndr_queue.py) permits only ONE intelligence_results row per
        engagement_id, ever - a second distinct submission raises engagement_already_has_result.
        Exotel's transcript webhook fires once per conversational turn, so without this guard
        the Brain would attempt a submission on every turn: an early ambiguous turn (UNCLEAR)
        would claim the one allowed slot, and a customer's real, later, decisive answer would
        be silently dropped when ShopDeck rejects it.

        Returns True only for the caller that wins the race (the one allowed to actually POST
        to ShopDeck); False means another turn already claimed it and this caller must not
        submit. The filter matches only documents with no metadata.intelligence_result_id yet,
        so under concurrent transcript events at most one update_one call can succeed.
        """
        db = await self._get_db()
        res = await db.customer_engagements.update_one(
            {
                "engagement_id": engagement_id,
                "metadata.intelligence_result_id": {"$exists": False},
            },
            {
                "$set": {
                    "metadata.intelligence_result_id": result_id,
                    "metadata.intelligence_submitted_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return res.modified_count > 0
