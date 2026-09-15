import asyncio
import logging
import urllib.parse
from typing import Optional

import boto3
import httpx

from src.shared.config import settings

logger = logging.getLogger(__name__)


async def fetch_and_store_recording(interaction_id: str, awb_no: str, engagement_id: str) -> Optional[str]:
    """
    Fetches a call recording from Sarvam's analytics/recordings API (keyed by interaction_id
    - the completion webhook's own recording_url field has been observed null on every real
    call, so this pull-based endpoint is the only working path, confirmed 2026-09-15) and
    re-hosts it on Cloudflare R2, since ShopDeck's recording_url column expects a plain link,
    not raw audio bytes, and Sarvam's endpoint returns the actual WAV file directly.

    Returns the public URL on success, or None on any failure - a recording is supplementary
    evidence, not something that should ever block the rest of the call-completed webhook's
    outcome-writeback logic. Callers must not raise this exception onward.

    Known limitation: this call is synchronous within the webhook handler with no retry -
    unlike the ndr_intelligence_results outbox, a transient Sarvam/R2 failure here means that
    call's recording is simply never stored, since Sarvam sends this webhook exactly once.
    """
    if not settings.r2_aaram_ndr_call_recording_bucket:
        logger.info("R2 recording storage not configured - skipping recording fetch for engagement %s.", engagement_id)
        return None

    try:
        org = settings.sarvam_org_id
        ws = settings.sarvam_workspace_id
        agent = settings.sarvam_agent_id
        encoded_interaction_id = urllib.parse.quote(interaction_id, safe="")
        url = f"https://apps.sarvam.ai/api/analytics/v1/{org}/{ws}/{agent}/recordings/{encoded_interaction_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"X-API-Key": settings.sarvam_api_key})
        resp.raise_for_status()

        if not resp.content.startswith(b"RIFF"):
            logger.error(
                "Sarvam recording response for engagement %s doesn't look like a WAV file (content-type=%s) - not storing.",
                engagement_id, resp.headers.get("content-type"),
            )
            return None

        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.r2_s3_client_endpoint,
            aws_access_key_id=settings.r2_aaram_ndr_call_recording_access_id,
            aws_secret_access_key=settings.r2_aaram_ndr_call_recording_access_key,
            region_name="auto",
        )
        key = f"sarvam_call_recordings/{awb_no}/{engagement_id}.wav"
        # boto3 is synchronous - run it off the event loop so a multi-MB upload doesn't
        # stall other concurrent requests this FastAPI process is handling.
        await asyncio.to_thread(
            s3_client.put_object,
            Bucket=settings.r2_aaram_ndr_call_recording_bucket,
            Key=key,
            Body=resp.content,
            ContentType="audio/wav",
        )

        public_url = f"{settings.r2_aaram_ndr_call_recording_url.rstrip('/')}/{key}"
        logger.info("Stored recording for engagement %s at %s (%d bytes)", engagement_id, public_url, len(resp.content))
        return public_url

    except Exception as e:
        logger.error("Failed to fetch/store recording for engagement %s (interaction_id=%s): %s", engagement_id, interaction_id, e)
        return None
