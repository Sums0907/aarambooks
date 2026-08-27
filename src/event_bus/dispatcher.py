import json
from src.brain_core.action_engine.contracts import ActionRequest

class OutboundDispatcher:
    """Serializes ActionRequests into a safe outbound representation."""
    
    @staticmethod
    def dispatch(action: ActionRequest) -> str:
        """
        Accepts a governed ActionRequest and serializes it for broadcast.
        Does NOT execute the action.
        """
        if not isinstance(action, ActionRequest):
            raise ValueError("Dispatcher only accepts ActionRequest objects.")
            
        # Pydantic dump
        payload = action.model_dump(mode="json")
        
        # Wrap in standard event envelope
        event = {
            "event_type": "action_dispatched",
            "payload": payload
        }
        
        return json.dumps(event)
