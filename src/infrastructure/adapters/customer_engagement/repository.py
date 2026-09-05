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

    async def create_engagement(self, record: CustomerEngagementRecord) -> None:
        db = await self._get_db()
        doc = record.model_dump()
        doc["normalization_status"] = NormalizationStatus.NOT_READY
        doc["created_at"] = datetime.now(UTC)
        doc["updated_at"] = doc["created_at"]
        await db.customer_engagements.insert_one(doc)

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
