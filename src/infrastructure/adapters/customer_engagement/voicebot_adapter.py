from typing import Any, Dict, Protocol, runtime_checkable

from src.brain_core.action_engine.contracts import ActionRequest


@runtime_checkable
class VoiceBotAdapter(Protocol):
    """
    Structural contract every voice-bot provider adapter must satisfy to plug into
    CustomerEngagementExecutor. Python Protocols use structural typing, so an existing
    adapter (e.g. ExotelVoiceBotAdapter) conforms automatically as long as it has a matching
    `provider_name` attribute and `dispatch_call` method - no inheritance required, and no
    change to an existing adapter's behavior needed beyond declaring `provider_name`.

    This only covers outbound call dispatch. Inbound webhook/hook handling (building the
    per-call context variables, parsing the provider's own transcript/outcome payload shape)
    is intentionally NOT part of this protocol - each provider's webhook shape is different
    enough (Exotel's session-start/transcript/session-end webhooks vs Sarvam's on-start/
    on-end hooks) that forcing them into one interface would either leak provider-specific
    detail into the shared contract or force premature abstraction before a second real
    provider exists. The provider-agnostic pieces that DO exist (NDR transcript
    classification, reattempt-date matching) already live in
    src/intelligence_domains/ndr/reply_parser.py, shared by calling into the same functions
    from each provider's own webhook handler.
    """

    provider_name: str

    async def dispatch_call(self, action_request: ActionRequest, engagement_id: str) -> Dict[str, Any]:
        """Places the outbound call. Returns at least {"call_id": <provider's call/session id>}."""
        ...
