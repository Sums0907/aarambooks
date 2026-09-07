from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from src.infrastructure.mongo_client import get_mongo_db

class CommunicationRepository:
    """
    Repository for persisting and retrieving unstructured customer interactions
    (WhatsApp chat histories, IVR logs, SMS replies) for the NDR domain.
    """
    def __init__(self):
        # We fetch the DB lazily to ensure the app has started and connected
        self._db = None

    async def _get_collection(self):
        if self._db is None:
            self._db = await get_mongo_db()
        return self._db["customer_interactions"]

    async def log_interaction(
        self,
        awb_no: str,
        channel: str,  # 'whatsapp', 'ivr', 'sms'
        direction: str, # 'outbound', 'inbound'
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Logs a single interaction event for a specific AWB.
        Returns the inserted document ID as a string.
        """
        collection = await self._get_collection()
        
        document = {
            "awb_no": awb_no,
            "channel": channel,
            "direction": direction,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC)
        }
        
        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def get_history(self, awb_no: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the interaction history for a given AWB, sorted by timestamp (oldest first).
        """
        collection = await self._get_collection()
        cursor = collection.find({"awb_no": awb_no}).sort("timestamp", 1).limit(limit)
        
        history = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
            history.append(doc)
            
        return history
