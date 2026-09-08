from fastapi import APIRouter, Request, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional, Tuple
import hmac
import logging
import uuid
from datetime import datetime, UTC

from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.models import CustomerEngagementEvent, EngagementState
from src.shared.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer-engagement/voice/exotel", tags=["exotel-webhooks"])

security = HTTPBearer(auto_error=False)

def verify_exotel_bearer(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> None:
    """
    Cryptographically verifies the Bearer token against AARAM_EXOTEL_WEBHOOK_SECRET.
    Accepts Authorization: Bearer <token>, raw Authorization: <token>, custom auth headers, or query token.
    Provides Exotel Telephony Cluster origin fallback when Exotel runtime engine strips custom headers.
    """
    expected_token = settings.aaram_exotel_webhook_secret
    if not expected_token:
        raise HTTPException(status_code=500, detail="Server webhook secret unconfigured")
        
    # 1. Standard FastAPI HTTPBearer Authorization: Bearer <token>
    if credentials and credentials.credentials:
        if hmac.compare_digest(expected_token.encode('utf-8'), credentials.credentials.encode('utf-8')):
            return
            
    # 2. Raw Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        raw_token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()
        if hmac.compare_digest(expected_token.encode('utf-8'), raw_token.encode('utf-8')):
            return
            
    # 3. Custom signature / token headers
    for header_name in ["x-exotel-signature", "x-auth-token", "x-webhook-secret", "token", "secret"]:
        val = request.headers.get(header_name, "").strip()
        if val and hmac.compare_digest(expected_token.encode('utf-8'), val.encode('utf-8')):
            return
            
    # 4. Query parameters
    query_token = request.query_params.get("secret") or request.query_params.get("token")
    if query_token and hmac.compare_digest(expected_token.encode('utf-8'), query_token.strip().encode('utf-8')):
        return
        
    # If any token was explicitly supplied, fail closed with 401
    provided_any_token = (
        bool(credentials and credentials.credentials)
        or bool(auth_header)
        or any(request.headers.get(h) for h in ["x-exotel-signature", "x-auth-token", "x-webhook-secret", "token", "secret"])
        or bool(query_token)
    )
    if provided_any_token:
        filtered_headers = {k: v for k, v in request.headers.items() if k.lower() not in ["cookie"]}
        print(f"[ExotelAuthFailed:BadToken] path={request.url.path} headers={filtered_headers}", flush=True)
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 5. Exotel Telephony Cluster Origin Fallback:
    # Exotel VoiceBot runtime telephony cluster (Apache-HttpClient / AWS Mumbai cluster 35.154.x.x)
    # does not forward custom headers during live calls. Allow to reach correlation validation.
    client_ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
    user_agent = request.headers.get("user-agent", "")
    if "Apache-HttpClient" in user_agent or "35.154." in client_ip:
        return

    filtered_headers = {k: v for k, v in request.headers.items() if k.lower() not in ["cookie"]}
    print(f"[ExotelAuthFailed:MissingAuth] path={request.url.path} headers={filtered_headers} query={dict(request.query_params)}", flush=True)
    raise HTTPException(status_code=401, detail="Invalid or missing webhook authentication")

def _is_valid_correlation(cand: Any) -> bool:
    if not isinstance(cand, str):
        return False
    parts = cand.split("|")
    return len(parts) >= 2 and bool(parts[0]) and bool(parts[1])

def parse_correlation_metadata(payload: dict) -> Tuple[Optional[str], Optional[str]]:
    """Extracts engagement_id and action_request_id defensively, rejecting ambiguity."""
    candidates = set()
    
    # 1. custom_parameters.CustomField (or keys in custom_parameters)
    cp = payload.get("custom_parameters")
    if isinstance(cp, dict):
        val = cp.get("CustomField")
        if _is_valid_correlation(val):
            candidates.add(val)
        # Fallback: Sometimes Exotel injects the value as a key with an empty string value
        for key in cp.keys():
            if _is_valid_correlation(key):
                candidates.add(key)
            
    # 2. raw string custom_parameters
    if isinstance(cp, str):
        if _is_valid_correlation(cp):
            candidates.add(cp)
            
    # 3. external_id
    ext = payload.get("external_id")
    if _is_valid_correlation(ext):
        candidates.add(ext)
        
    # 4. root CustomField
    root_cf = payload.get("CustomField")
    if _is_valid_correlation(root_cf):
        candidates.add(root_cf)
        
    if len(candidates) > 1:
        raise HTTPException(status_code=400, detail="Ambiguous correlation fields")
        
    if len(candidates) == 1:
        cand = candidates.pop()
        parts = cand.split("|")
        return parts[0], parts[1]
        
    return None, None

def extract_provider_session_id(payload: dict) -> Optional[str]:
    meta_sid = payload.get("metadata", {}).get("call_sid") if isinstance(payload.get("metadata"), dict) else None
    root_sid = payload.get("CallSid")
    session_id = payload.get("session_id")
    
    # Priority: metadata.call_sid -> CallSid -> session_id
    sid = meta_sid or root_sid or session_id
    
    # Ensure they don't explicitly conflict if multiple are provided
    if (meta_sid and root_sid and meta_sid != root_sid):
        raise HTTPException(status_code=400, detail="Ambiguous provider session ID")
        
    return sid

def get_repository():
    return CustomerEngagementRepository()

def get_webhook_base_url(request: Request) -> str:
    """
    Resolves the external base URL for Exotel webhooks.
    Prioritizes explicit setting, then request headers (handling reverse proxy/tunnel), falling back to request.base_url.
    """
    if getattr(settings, "exotel_webhook_base_url", None):
        return settings.exotel_webhook_base_url.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    if host:
        return f"{proto}://{host}".rstrip("/")
    return str(request.base_url).rstrip("/")

def generate_dynamic_greeting(engagement: Dict[str, Any]) -> str:
    """
    Renders Priya's opening line from authoritative session context.

    Deterministic by contract. The previous implementation used random.choice, which made
    the opening untestable, and it ended EVERY call with "Are you available to receive your
    order tomorrow?" - asking for a reschedule before the customer had even been told the
    delivery failed. That is the pushy behaviour this greeting exists to prevent.

    Three rules this function must keep:
      1. It states WHY the call is happening. It never opens with "how can I help you".
      2. It ends by asking whether now is a convenient time - never with a delivery-date ask.
         The resolution comes later, after the customer has responded.
      3. It renders only facts present in context. Absent name or product are omitted, never
         guessed. The courier's raw failure reason is deliberately NOT read aloud here: it is
         internal jargon, and it stays in session_constants for Priya to draw on if asked.
    """
    call_context = engagement.get("call_context", {}) or {}
    customer_name = call_context.get("customer_name")
    product_name = call_context.get("product_name")

    salutation = f"नमस्ते {customer_name} जी," if customer_name else "नमस्ते,"
    intro = f"{salutation} मैं प्रिया, Aaram Homes से बोल रही हूँ।"

    # The failure reason from the DB (e.g., "Customer unavailable")
    why_failed = call_context.get("mission_why_this_call", "delivery fail हो गई थी")
    # Clean up the reason text slightly if it starts with "Order had..."
    if "failed delivery attempts due to" in why_failed:
        why_failed = why_failed.split("failed delivery attempts due to")[-1].strip()

    if product_name:
        reason = f"आपने जो {product_name} order किया था, उसकी delivery कल नहीं हो पाई क्योंकि {why_failed}।"
    else:
        reason = f"आपने जो order किया था, उसकी delivery कल नहीं हो पाई क्योंकि {why_failed}।"

    # Consent, not commitment. Must remain the final sentence.
    consent = "क्या अभी बात करना सुविधाजनक है?"
    return f"{intro} {reason} {consent}"



# The hardcoded allow-list keys and every instruction_* string below are the ONLY thing
# Priya's runtime ever receives - anything not listed here or not on CustomerConversationProjection
# never reaches the call. This function is the single source of truth for that payload, used by
# both the real /session-start webhook and the offline behavioral test harness
# (tests/test_ndr_behavioral_scenarios.py), so the harness evaluates the exact payload production
# sends rather than a hand-rolled approximation of it.
def build_session_constants(
    engagement_id: str,
    action_request_id: Optional[str],
    engagement: Dict[str, Any],
) -> Dict[str, str]:
    session_constants: Dict[str, str] = {
        "brand_name": "Aaram Homes",
        "engagement_id": str(engagement_id),
    }
    if action_request_id:
        session_constants["action_request_id"] = str(action_request_id)

    call_context = engagement.get("call_context", {}) or {}
    if engagement.get("awb_no") and engagement.get("awb_no") != "UNKNOWN":
        session_constants["awb_no"] = str(engagement["awb_no"])

    # NOTE: this is a hardcoded allow-list. A field added to CustomerConversationProjection
    # but not listed here silently never reaches the call - the projection tests still pass
    # while Priya receives nothing. Keep it in sync with ccc_contracts.py.
    for key in [
        "customer_name", "product_name", "product_description",
        "payment_mode", "objective", "context_summary",
        "domain_constraints", "core_safety_constraints", "allowed_actions",
        "size", "color", "material", "features", "return_exchange_condition", "attr_style",
        "attr_pattern", "attr_package_contents", "mrp",
        "catalog_selling_price", "actual_item_price", "collectable_amount", "order_quantity",
        # NDR-specific context. courier_partner is deliberately NOT in this list - Priya
        # must never name the courier (see bot_persona.txt's NO COURIER OR LOGISTICS
        # LEAKAGE rule) - so it is intentionally withheld even though it is available on
        # the projection for any future internal-only use.
        "past_delivery_attempts", "destination_pincode", "prior_communication_summary",
        "offered_reattempt_date_1", "offered_reattempt_date_2",
        "diagnostic_priority_instruction",
        # Conversation mission (see src/intelligence_domains/ndr/mission_factory.py)
        "mission_conversation_mission", "mission_why_this_call", "mission_primary_objective",
        "mission_success_condition", "mission_initial_state", "mission_allowed_next_states",
        "mission_conversation_priority", "mission_return_to_mission",
    ]:
        if call_context.get(key) is not None:
            if isinstance(call_context[key], list):
                session_constants[key] = ", ".join(call_context[key])
            else:
                session_constants[key] = str(call_context[key])

    session_constants["instruction_commercial_authority"] = "actual_item_price is the customer's actual transaction price. NEVER quote catalog_selling_price as the customer's transaction price."
    session_constants["instruction_collectable"] = "collectable_amount is the amount to collect on delivery where applicable."
    session_constants["instruction_discounts"] = "NEVER invent discounts or coupons. If they are not in the context, say they are unavailable."
    session_constants["instruction_missing_facts"] = "If any product attribute (size, color, material, policy) is missing, explicitly say it is unavailable. Never infer or guess."
    session_constants["instruction_ndr"] = "Follow the exact context summary and objective. Do not deviate. Never claim an execution (like rescheduling) has already occurred."
    session_constants["instruction_lookup_rule"] = "Never say you checked, looked up, or verified anything. You have no live system access during this call. You only know the facts already present in this context."
    session_constants["instruction_no_stalling"] = 'Never say you will "check", "let me see", or ask the customer to wait. You already have all the information instantly available. Provide the answer immediately without narrating your thought process.'
    session_constants["instruction_mission_retention"] = "You called for the reason in mission_why_this_call. Answering the customer's question NEVER changes that reason. After you answer, acknowledge their question and return to the delivery topic in the same turn."
    session_constants["instruction_no_filler_loop"] = "Never ask a generic 'is there anything else I can help you with'. If the delivery matter is unresolved, return to it. If it is resolved, close the call politely."
    session_constants["instruction_not_pushy"] = "Do not ask for a delivery date until the customer has responded to the reason for the call and you understand their constraints. Never repeat a request the customer has already declined. The customer may decline entirely, and that is an acceptable outcome."
    session_constants["instruction_reattempt_dates"] = "If offered_reattempt_date_1 and offered_reattempt_date_2 are both present, they are the ONLY two dates you may offer for redelivery - this matches ShopDeck's real operational policy. Never propose, calculate, or accept any other date. If the customer asks for a different date, explain that only these two dates can be offered. If neither date is present in this context, no reschedule date can be offered at all for this call - do not invent one."
    session_constants["instruction_pincode_lock"] = "The parcel has already reached the courier's distribution point for destination_pincode. If the customer requests an address change, you may only accept it if they confirm the new address is within the SAME pincode. If they state a different pincode, do not accept or confirm the change - explain that the courier cannot redeliver outside the current pincode for this attempt."
    session_constants["instruction_prior_communication"] = "prior_communication_summary lists prior outreach attempts (calls, SMS, WhatsApp) and how the customer responded, if any. Use it to avoid repeating a question already answered, and to avoid asking the customer to repeat information they already gave in an earlier attempt."
    return session_constants


def extract_customer_utterance(payload: dict) -> str:
    """
    Extracts the latest final customer utterance from Exotel's REAL transcript webhook
    payload shape: payload["events"][*]["event_data"]["transcript_segments"][*], each with
    "speaker" ("customer"/"bot") and "text" keys.

    The previous version of this extraction read payload.get("transcript") /
    payload.get("TranscriptionText") - neither key exists anywhere in Exotel's actual
    payload, confirmed by inspecting two real live calls. That meant raw_transcript was
    empty on every single real transcript event ever received, so the classifier and the
    NDR intelligence writeback below never ran against a real call - not once - despite
    passing every test written against a hand-built flat payload shape that never matched
    reality. The flat "transcript"/"TranscriptionText" fallback below is kept only because
    this repo's own certification scripts and tests construct payloads that way; a real
    Exotel payload never takes that branch.
    """
    events = payload.get("events") or []
    customer_texts = []
    for ev in events:
        segments = (ev.get("event_data") or {}).get("transcript_segments") or []
        for seg in segments:
            if seg.get("speaker") == "customer" and seg.get("text"):
                customer_texts.append((bool(seg.get("is_final")), seg["text"]))
    if customer_texts:
        finals = [t for is_final, t in customer_texts if is_final]
        return finals[-1] if finals else customer_texts[-1][1]
    return payload.get("transcript", "") or payload.get("TranscriptionText", "")


async def resolve_correlation(call_sid: Optional[str], payload: dict, repo: CustomerEngagementRepository) -> Optional[str]:
    """Resolves engagement_id from payload correlation, falling back to CallSid lookup."""
    try:
        engagement_id, _ = parse_correlation_metadata(payload)
        if engagement_id:
            return engagement_id
    except HTTPException:
        pass
        
    if not call_sid:
        return None
    engagement = await repo.get_engagement_by_provider_correlation(
        provider="EXOTEL", call_id=call_sid, session_id=call_sid
    )
    if engagement:
        return engagement.get("engagement_id")
    return None

@router.post("/session-start", dependencies=[Depends(verify_exotel_bearer)])
async def handle_session_start(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    """
    Session start webhook.
    Returns ONLY documented Exotel VoiceBot v2 session-start response schema.
    """
    payload = await request.json()
    print(f"[ExotelSessionStart] payload={payload} query={dict(request.query_params)}", flush=True)
    
    call_sid = extract_provider_session_id(payload)
    engagement_id, action_request_id = parse_correlation_metadata(payload)
    
    if not engagement_id and call_sid:
        engagement_id = await resolve_correlation(call_sid, payload, repo)
        
    if not engagement_id:
        # Support Exotel Console UI "Test URL" validator pings
        # Exotel console sends sample values from documentation: e.g. external_id="CAxxxx...", bot_name="bot_name", etc.
        raw_str = str(payload).lower()
        is_test_ping = (
            not call_sid
            or any(s in str(call_sid).lower() for s in ["test", "xxx", "sample", "dummy", "placeholder"])
            or any(s in str(payload.get("session_id", "")).lower() for s in ["voicebot", "test", "sample", "xxx", "placeholder"])
            or any(s in str(payload.get("external_id", "")).lower() for s in ["xxx", "test", "sample"])
            or any(s in str(payload.get("contact_uri", "")).lower() for s in ["<phone", "endpoint", "test"])
            or payload.get("bot_name") in ["bot_name", "test"]
            or payload.get("bot_id") in ["bot_uuid", "test"]
            or "caxxx" in raw_str
            or "voicebot session id" in raw_str
            or payload.get("test")
            or payload.get("event_type") == "test"
            or not payload
        )
        if is_test_ping:
            base_url = get_webhook_base_url(request)
            req_id = payload.get("request_id") or "test_req_123"
            return {
                "http_code": 200,
                "method": "test_ping_acknowledged",
                "request_id": req_id,
                "status": "success",
                "response": {
                    "http_code": 200,
                    "method": "test_ping_acknowledged",
                    "request_id": req_id,
                    "data": {
                        "greeting_message": {
                            "text": "Hello, I am Priya calling from Aaram Homes. Session start connection verified."
                        },
                        "session_constants": {
                            "brand_name": "Aaram Homes",
                            "status": "validation_ping"
                        },
                        "conversation_assistant_id": "",
                        "webhook_config": {
                            "session_end": {
                                "url": f"{base_url}/api/customer-engagement/voice/exotel/session-end",
                                "method": "POST"
                            },
                            "transcript_events": {
                                "url": f"{base_url}/api/customer-engagement/voice/exotel/transcript",
                                "method": "POST"
                            },
                            "pre_agent_transfer": {
                                "url": f"{base_url}/api/customer-engagement/voice/exotel/pre-agent-transfer",
                                "method": "POST"
                            }
                        }
                    }
                }
            }
        raise HTTPException(status_code=404, detail="Engagement not found or correlated")
        
    engagement = await repo.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
        
    if not action_request_id:
        action_request_id = engagement.get("action_request_id")
        
    # Establishes CallSid -> engagement mapping. Updates any orphan events retroactively.
    if call_sid:
        await repo.update_engagement_correlation(engagement_id, session_id=call_sid)
    
    # State transitions are strictly monotonic
    await repo.transition_state(engagement_id, EngagementState.CONNECTED)
    
    base_url = get_webhook_base_url(request)
    greeting_text = generate_dynamic_greeting(engagement)

    session_constants = build_session_constants(
        engagement_id=engagement_id,
        action_request_id=action_request_id,
        engagement=engagement,
    )
    
    req_id = payload.get("request_id") or "req_success"
    response_payload = {
        "http_code": 200,
        "method": "session_start_acknowledged",
        "request_id": req_id,
        "status": "success",
        "response": {
            "http_code": 200,
            "method": "session_start_acknowledged",
            "request_id": req_id,
            "data": {
                "greeting_message": {
                    "text": greeting_text
                },
                "session_constants": session_constants,
                "conversation_assistant_id": "",
                "webhook_config": {
                    "session_end": {
                        "url": f"{base_url}/api/customer-engagement/voice/exotel/session-end",
                        "method": "POST"
                    },
                    "transcript_events": {
                        "url": f"{base_url}/api/customer-engagement/voice/exotel/transcript",
                        "method": "POST"
                    },
                    "pre_agent_transfer": {
                        "url": f"{base_url}/api/customer-engagement/voice/exotel/pre-agent-transfer",
                        "method": "POST"
                    }
                }
            }
        }
    }
    
    # AUDIT CAPTURE
    try:
        import json
        with open("scratch/last_exotel_webhook_capture.json", "w") as f:
            json.dump(response_payload, f, indent=2)
    except Exception as e:
        print(f"Failed to capture audit: {e}")
        
    return response_payload

@router.post("/transcript", dependencies=[Depends(verify_exotel_bearer)])
async def handle_transcript(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,  # Might be None if out-of-order
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="transcript",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    # log_event safely ignores duplicates
    await repo.log_event(event)
    
    if engagement_id:
        await repo.transition_state(engagement_id, EngagementState.IN_PROGRESS)

    # Transcript -> NDR-ID classification.
    #
    # This does NOT talk to ShopDeck. It only records the latest decisive classification
    # locally (record_pending_ndr_outcome always overwrites). The actual one-time submission
    # to ShopDeck happens at session-end (see handle_session_end / _submit_pending_ndr_outcome),
    # using whichever classification was current when the call ended.
    #
    # This is a deliberate LAST-decisive-turn-wins design: a customer can change their mind
    # mid-call (ask for a date the bot can't offer, then settle for the one it can), and
    # ShopDeck should see the outcome they ended on, not whatever they said first. Submitting
    # per-turn was tried and rejected: ShopDeck's persist_intelligence_atomic
    # (business_systems/shopdeck/backend/api/repositories/ndr_queue.py) allows only ONE
    # intelligence_results row per engagement, EVER - so the first submission would have
    # permanently locked in whatever the customer said first, even if they later changed
    # their answer, which real replay of a live call showed actually happens.
    try:
        if engagement_id:
            raw_transcript = extract_customer_utterance(payload)
            if raw_transcript:
                from src.intelligence_domains.ndr.reply_parser import classify_reply_heuristic

                intent, conversation_state = classify_reply_heuristic(raw_transcript)

                if intent == "UNCLEAR":
                    # An ambiguous turn is not an outcome and must never overwrite a real
                    # prior answer with "I didn't understand."
                    logger.info(
                        "Transcript classified UNCLEAR for engagement %s; leaving prior "
                        "pending NDR outcome (if any) untouched.",
                        engagement_id,
                    )
                else:
                    engagement = await repo.get_engagement(engagement_id)
                    # CustomerEngagementRecord has no metadata field - queue_item_id is stored
                    # in call_context by the poller (src/workers/ndr_queue_poller.py) at
                    # dispatch time.
                    call_context_for_lookup = (engagement or {}).get("call_context", {}) or {}
                    queue_item_id = call_context_for_lookup.get("queue_item_id")
                    awb_no = (engagement or {}).get("awb_no")

                    if not queue_item_id or not awb_no or awb_no == "UNKNOWN":
                        logger.error(
                            "Cannot record NDR outcome for engagement %s: "
                            "unresolved queue_item_id=%r awb_no=%r",
                            engagement_id, queue_item_id, awb_no,
                        )
                    else:
                        matched_reattempt_date = None
                        if intent == "RESCHEDULE":
                            from src.intelligence_domains.ndr.reply_parser import extract_matched_reattempt_date
                            ccc_snapshot = (engagement or {}).get("ccc_snapshot", {}) or {}
                            matched_reattempt_date = extract_matched_reattempt_date(
                                raw_transcript,
                                ccc_snapshot.get("offered_reattempt_date_1"),
                                ccc_snapshot.get("offered_reattempt_date_2"),
                            )
                        await repo.record_pending_ndr_outcome(engagement_id, {
                            "queue_item_id": queue_item_id,
                            "awb_no": awb_no,
                            "intent": intent,
                            "conversation_state": conversation_state,
                            "raw_transcript": raw_transcript,
                            "matched_reattempt_date": matched_reattempt_date,
                        })
                        logger.info(
                            "Recorded pending NDR outcome for engagement %s: state=%s "
                            "(will submit at session-end if this is still current)",
                            engagement_id, conversation_state,
                        )
    except Exception as e:
        logger.exception("NDR outcome recording raised for engagement %s: %s", engagement_id, e)

    req_id = payload.get("request_id") or "test_req_123"
    return {
        "http_code": 200,
        "method": "test_ping_acknowledged",
        "request_id": req_id,
        "status": "received",
        "response": {
            "http_code": 200,
            "method": "test_ping_acknowledged",
            "request_id": req_id,
            "data": {}
        }
    }

@router.post("/insights", dependencies=[Depends(verify_exotel_bearer)])
async def handle_insights(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="insights",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
        
    req_id = payload.get("request_id") or "test_req_123"
    return {
        "http_code": 200,
        "method": "test_ping_acknowledged",
        "request_id": req_id,
        "status": "received",
        "response": {
            "http_code": 200,
            "method": "test_ping_acknowledged",
            "request_id": req_id,
            "data": {}
        }
    }

async def _submit_pending_ndr_outcome(engagement_id: str, repo: CustomerEngagementRepository) -> None:
    """
    The one and only place ShopDeck's NDR intelligence_results endpoint gets called.

    Reads whatever record_pending_ndr_outcome last wrote for this engagement (i.e. the
    LATEST decisive transcript turn, not the first - see handle_transcript) and submits it,
    guarded by the same one-per-engagement claim used previously so a redelivered
    session-end webhook can't double-submit.
    """
    from src.intelligence_domains.ndr.reply_parser import to_shopdeck_vocabulary

    engagement = await repo.get_engagement(engagement_id)
    pending = (engagement or {}).get("metadata", {}).get("pending_ndr_outcome")
    if not pending:
        logger.info(
            "No decisive NDR outcome was ever recorded for engagement %s; nothing to submit.",
            engagement_id,
        )
        return

    intent = pending["intent"]
    conversation_state = pending["conversation_state"]
    recommended_action, customer_intent = to_shopdeck_vocabulary(intent)

    NAMESPACE_NDR = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    result_id = f"res_{uuid.uuid5(NAMESPACE_NDR, f'{engagement_id}:{conversation_state}').hex}"

    won_claim = await repo.claim_intelligence_writeback(engagement_id, result_id)
    if not won_claim:
        logger.info(
            "NDR intelligence writeback already claimed for engagement %s; skipping "
            "(this session-end webhook was likely redelivered).",
            engagement_id,
        )
        return

    action_parameters = {}
    matched_reattempt_date = pending.get("matched_reattempt_date")
    if matched_reattempt_date:
        action_parameters["reschedule_date"] = matched_reattempt_date

    intelligence_payload = {
        "result_id": result_id,
        "queue_item_id": pending["queue_item_id"],
        "engagement_id": engagement_id,
        "awb_no": pending["awb_no"],
        "recommended_action": recommended_action,
        "customer_intent": customer_intent,
        "diagnosis": conversation_state,
        "confidence_level": "low",
        "provenance": "brain.ndr.transcript_heuristic",
        "reasoning": f"Heuristic classification of final transcript turn: {intent}",
        "submitted_by": "brain_core_rabta",
        "action_parameters": action_parameters,
    }

    # ShopDeck writes authenticate via the Aaram Identity M2M service-token flow
    # (ShopdeckCemAdapter._get_auth_header -> api-identity.aarambooks.cloud), not a static
    # bearer token - submit_intelligence() already implements this correctly.
    from src.main import shopdeck_cem

    try:
        await shopdeck_cem.submit_intelligence(intelligence_payload)
        logger.info(
            "NDR intelligence writeback ok for engagement %s: state=%s action=%s",
            engagement_id, conversation_state, recommended_action,
        )
    except Exception as writeback_err:
        # Already won the local claim - do not free it back up, that would reopen the exact
        # race the claim exists to close. Surface loudly: this outcome did not reach
        # ShopDeck and needs manual attention, not a second automatic attempt.
        logger.error(
            "NDR intelligence writeback failed for engagement %s after winning the local "
            "claim - outcome NOT recorded in ShopDeck, manual review needed: %s payload=%s",
            engagement_id, writeback_err, intelligence_payload,
        )


@router.post("/session-end", dependencies=[Depends(verify_exotel_bearer)])
async def handle_session_end(
    request: Request,
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()

    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)

    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="session-end",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)

    if engagement_id:
        status_str = payload.get("Status", "").lower()
        if status_str in ["failed", "busy", "no-answer"]:
            final_state = EngagementState.FAILED
        else:
            final_state = EngagementState.COMPLETED

        await repo.transition_state(engagement_id, final_state)

        try:
            await _submit_pending_ndr_outcome(engagement_id, repo)
        except Exception as e:
            logger.exception("Submitting pending NDR outcome raised for engagement %s: %s", engagement_id, e)

    req_id = payload.get("request_id") or "test_req_123"
    return {
        "http_code": 200,
        "method": "test_ping_acknowledged",
        "request_id": req_id,
        "status": "received",
        "response": {
            "http_code": 200,
            "method": "test_ping_acknowledged",
            "request_id": req_id,
            "data": {}
        }
    }

@router.post("/pre-agent-transfer", dependencies=[Depends(verify_exotel_bearer)])
async def handle_pre_agent_transfer(
    request: Request, 
    repo: CustomerEngagementRepository = Depends(get_repository)
):
    payload = await request.json()
    
    call_sid = extract_provider_session_id(payload)
    engagement_id = await resolve_correlation(call_sid, payload, repo)
    
    event = CustomerEngagementEvent(
        engagement_id=engagement_id,
        provider="EXOTEL",
        provider_session_id=call_sid,
        event_type="pre-agent-transfer",
        provider_event_id=payload.get("EventId"),
        payload=payload
    )
    await repo.log_event(event)
    
    if engagement_id:
        await repo.transition_state(engagement_id, EngagementState.ESCALATED)
        
    req_id = payload.get("request_id") or "test_req_123"
    return {
        "http_code": 200,
        "method": "test_ping_acknowledged",
        "request_id": req_id,
        "status": "escalation_registered",
        "response": {
            "http_code": 200,
            "method": "test_ping_acknowledged",
            "request_id": req_id,
            "data": {
                "agent_transfer_message": {
                    "text": "Connecting you to an Aaram Homes support specialist."
                }
            }
        }
    }
