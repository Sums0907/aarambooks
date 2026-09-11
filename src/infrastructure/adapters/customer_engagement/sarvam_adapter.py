import httpx
import logging
from typing import Any, Dict

from src.shared.config import settings
from src.brain_core.action_engine.contracts import ActionRequest
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.context_variables import build_provider_call_variables

logger = logging.getLogger(__name__)


class SarvamVoiceBotAdapter:
    """
    Physical execution adapter for Sarvam AI Voice Agents - Instant Outbound API.
    Implements POST /api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds,
    confirmed against real Sarvam docs (docs/claude/CONTEXT_HANDOFF_SARVAM_MIGRATION.md) -
    not a batch/campaign call, a genuine single-call trigger returning an immediate
    attempt_id, the closest match to Exotel's Calls/connect.json for this codebase's
    per-NDR-case dispatch model.

    Unlike Exotel (which fetches full call context via a separate session-start webhook
    pull), Sarvam needs the full variable set pushed in this same request
    (app_config.agent_variables) - so this adapter reads the engagement record it was just
    created with (see CustomerEngagementExecutor.prepare_engagement, which always runs
    before dispatch_call) to build that payload.
    """
    provider_name = "SARVAM"

    def __init__(self, repository: CustomerEngagementRepository):
        self.repository = repository
        self.api_key = settings.sarvam_api_key
        self.org_id = settings.sarvam_org_id
        self.workspace_id = settings.sarvam_workspace_id
        self.agent_id = settings.sarvam_agent_id
        self.app_version = settings.sarvam_app_version
        self.connection_id = settings.sarvam_connection_id
        self.agent_phone_number = settings.sarvam_phone_number
        self.webhook_base_url = settings.sarvam_webhook_base_url
        self.base_url = f"https://apps.sarvam.ai/api/outbounds/v1/orgs/{self.org_id}/workspaces/{self.workspace_id}"

    async def dispatch_call(self, action_request: ActionRequest, engagement_id: str) -> Dict[str, Any]:
        """
        Triggers an individual outbound call via Sarvam's Instant Outbound API.

        CRITICAL SAFETY RULE (same as ExotelVoiceBotAdapter):
        Outbound call creation is retry-unsafe - Sarvam's docs give no confirmed
        idempotency-key mechanism for this endpoint either. Fail fast and classify the
        error explicitly rather than risk a duplicate physical call via blind retry.
        """
        if not self.agent_id or not self.connection_id or not self.agent_phone_number:
            raise ValueError("Sarvam agent_id/connection_id/phone_number not fully configured.")

        customer_phone = action_request.parameters.get("customer_phone")

        if getattr(settings, "test_phone_override", ""):
            customer_phone = settings.test_phone_override
            logger.info(f"TEST MODE: Overriding customer phone to {customer_phone}")

        if not customer_phone:
            raise ValueError("Customer phone number missing in parameters.")

        # The engagement record (with call_context) already exists at this point -
        # CustomerEngagementExecutor.prepare_engagement() creates it before dispatch_call()
        # is ever invoked (see execute_engagement()).
        engagement = await self.repository.get_engagement(engagement_id)
        if not engagement:
            raise ValueError(f"Engagement {engagement_id} not found - cannot build agent_variables.")

        action_request_id = engagement.get("action_request_id")
        from src.shared.domain_contracts import IntelligenceDomain
        agent_variables = build_provider_call_variables(engagement_id, action_request_id, engagement, domain=IntelligenceDomain.NDR)

        endpoint = f"{self.base_url}/outbounds"

        app_config: Dict[str, Any] = {
            "app_id": self.agent_id,
            "app_version": self.app_version,
            "app_type": "agent",
            "connection_config": {
                "connection_id": self.connection_id,
                "agent_phone_number": self.agent_phone_number,
            },
            "agent_variables": agent_variables,
        }

        payload: Dict[str, Any] = {
            "app_config": app_config,
            "user_config": {"user_phone_number": customer_phone},
        }

        # webhook_config is optional per the docs, but without it there is no way to learn
        # the call's outcome - only omitted if no base URL is configured (e.g. local dev
        # with no tunnel running yet), in which case the call is fire-and-forget with no
        # completion signal, which is a real gap to notice rather than silently accept.
        if self.webhook_base_url:
            # webhook_config has no auth field at all (confirmed against real Instant
            # Outbound docs - only {url, metadata} exist), so the secret is embedded in the
            # URL itself as a query param, verified by verify_sarvam_bearer() on the
            # receiving end - the same query-token pattern already proven for Exotel, and
            # the only mechanism guaranteed to work here since there's no header for Sarvam
            # to carry a secret in even if it wanted to.
            webhook_url = f"{self.webhook_base_url.rstrip('/')}/api/customer-engagement/voice/sarvam/call-completed"
            if settings.sarvam_webhook_secret:
                webhook_url += f"?secret={settings.sarvam_webhook_secret}"
            else:
                logger.warning(
                    "SARVAM_WEBHOOK_SECRET not configured - dispatching call for engagement "
                    "%s with an unauthenticated completion webhook URL.",
                    engagement_id,
                )
            payload["webhook_config"] = {
                "url": webhook_url,
                "metadata": {
                    "engagement_id": engagement_id,
                    "action_request_id": action_request_id,
                },
            }
        else:
            logger.warning(
                "SARVAM_WEBHOOK_BASE_URL not configured - dispatching call for engagement "
                "%s with no webhook_config. Its outcome will never be reported back.",
                engagement_id,
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    headers={"X-API-Key": self.api_key},
                    json=payload,
                    timeout=10.0,
                )

            response.raise_for_status()
            data = response.json()

            return {
                "call_id": data.get("attempt_id"),
                "status": "dispatched",
            }

        except httpx.TimeoutException as e:
            logger.error(f"Sarvam outbound timeout for engagement {engagement_id}. Retry-unsafe: DO NOT auto-retry.")
            raise RuntimeError(f"Sarvam timeout: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                logger.error(f"Sarvam rate limit (429) for engagement {engagement_id}.")
            elif status >= 500:
                logger.error(f"Sarvam server error ({status}) for engagement {engagement_id}. Retry-unsafe.")
            else:
                logger.error(f"Sarvam permanent client error ({status}) for engagement {engagement_id}: {e.response.text}")
            raise RuntimeError(f"Sarvam HTTP {status}: {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Sarvam network failure for engagement {engagement_id}. Retry-unsafe.")
            raise RuntimeError(f"Sarvam network error: {str(e)}") from e
