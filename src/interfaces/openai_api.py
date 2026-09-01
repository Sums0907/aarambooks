from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time
import uuid
import httpx
import logging
import json
from src.shared.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["OpenAI Integration"])

async def get_m2m_token() -> Optional[str]:
    """Fetch a valid M2M token from AaramIdentity for physical routing."""
    if not settings.brain_client_id or not settings.brain_client_secret:
        return None
        
    url = f"{settings.identity_url.rstrip('/')}/auth/service-token"
    payload = {
        "client_id": settings.brain_client_id,
        "client_secret": settings.brain_client_secret
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("access_token")
            else:
                logger.error(f"Failed to fetch M2M token: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Error fetching M2M token: {e}")
        
    return None

from typing import List, Optional, Dict, Any, Union

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any], Dict[str, Any]]

def extract_text_content(content: Union[str, List[Any], Dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
                elif "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
        return "\n".join(parts)
    if isinstance(content, dict):
        return content.get("text") or content.get("content") or str(content)
    return str(content)

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]

def get_rabta_orchestrator(request: Request):
    orch = getattr(request.app.state, "rabta_orchestrator", None)
    if not orch:
        raise HTTPException(status_code=500, detail="Rabta orchestrator not configured.")
    return orch

from fastapi.responses import StreamingResponse
from src.brain_core.gateway.interfaces import GatewayGenerationRequest, GatewayMessage

async def classify_query_intent(gateway, user_query: str) -> dict:
    """
    R-1 Fast Intent Router: Decides whether to route to Azm (Aaram ERP) or Aalam (General AI).
    If Azm, it also decides which Intelligence Domain (inventory, shopdeck, ndr, etc.) to use.
    """
    lower_q = user_query.lower()
    
    # 1. Instant deterministic keyword check (0.01ms)
    inventory_keywords = ["sku", "stock", "inventory", "ledger", "balance", "warehouse", "bin", "batch", "quantity", "on-hand", "jobwork"]
    shopdeck_keywords = ["order", "shipping", "label", "revenue", "tax", "rto", "challan"]
    ndr_keywords = ["ndr", "delivery exception", "customer not available", "awb", "fake attempt", "delivery status", "failed delivery", "reschedule delivery", "reattempt"]
    
    domain = None
    if any(kw in lower_q for kw in inventory_keywords):
        domain = "inventory"
    elif any(kw in lower_q for kw in shopdeck_keywords):
        domain = "shopdeck"
    elif any(kw in lower_q for kw in ndr_keywords):
        domain = "ndr"
        
    if domain:
        return {
            "category": "AZM", 
            "id_urn": f"urn:aarambooks:intelligence:{domain}",
            "cem_urn": f"urn:aarambooks:cem:{domain}"
        }
        
    general_keywords = [
        "news", "weather", "trump", "who is", "what is the capital",
        "write a", "poem", "joke", "translate", "how to code", "python"
    ]
    if any(kw in lower_q for kw in general_keywords) or lower_q in ["hi", "hello", "hey", "help", "who are you"]:
        return {"category": "AALAM"}

    # 2. LLM Fallback for ambiguous queries
    system_prompt = """You are the Rabta Domain Router for AaramBooks.
Determine whether the user query is about AaramBooks business operations or general knowledge.
If business, specify the domain: 'inventory', 'shopdeck', 'ndr', or 'customer_query'.
Respond strictly with JSON: {"category": "AZM", "domain": "inventory"} or {"category": "AALAM"}"""
    try:
        req = GatewayGenerationRequest(
            messages=[
                GatewayMessage(role="system", content=system_prompt),
                GatewayMessage(role="user", content=user_query)
            ],
            model=settings.stage_r_1_intent_routing_model,
            temperature=0.0,
            max_tokens=25
        )
        res = await gateway.generate(req)
        text = res.content.strip()
        try:
            import json
            parsed = json.loads(text)
            if parsed.get("category") == "AZM":
                d = parsed.get("domain", "inventory")
                return {
                    "category": "AZM", 
                    "id_urn": f"urn:aarambooks:intelligence:{d}",
                    "cem_urn": f"urn:aarambooks:cem:{d}"
                }
        except:
            if "AZM" in text.upper():
                return {
                    "category": "AZM", 
                    "id_urn": "urn:aarambooks:intelligence:inventory",
                    "cem_urn": "urn:aarambooks:cem:inventory"
                }
    except Exception as e:
        logger.warning(f"Domain router fallback: {e}")
        
    return {"category": "AALAM"}

def clean_agent_tag(text: str) -> str:
    tags = [
        "🟢 ᴀᴀʟᴀᴍ ┃", "🟢 AALAM ┃", "🟢 [Aalam]", "🟢 [AALAM]", "🟢 aalam ┃",
        "🔸 ᴀᴢᴍ ┃", "🔸 AZM ┃", "🔸 [Azm]", "🔸 [AZM]", "🔸 azm ┃",
        "[Aalam]", "[Azm]", "[AALAM]", "[AZM]", "AALAM ┃", "AZM ┃"
    ]
    cleaned = text.strip()
    for t in tags:
        if cleaned.startswith(t):
            cleaned = cleaned[len(t):].strip()
        cleaned = cleaned.replace(t, "").strip()
    return cleaned

import asyncio
import re
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

def clean_search_keywords(q: str) -> str:
    cleaned = re.sub(r'[^\w\s]', ' ', q)
    stop_words = {'what', 'are', 'the', 'give', 'me', 'top', 'tell', 'show', 'can', 'you', 'please', 'about', 'who', 'is', 'was', 'were'}
    words = [w for w in cleaned.split() if w.lower() not in stop_words and not w.isdigit()]
    return ' '.join(words) if words else cleaned

async def search_live_web(query: str, max_results: int = 5) -> str:
    """Fetches real-time web search results using DDGS asynchronously."""
    def _do_search():
        try:
            kw = clean_search_keywords(query)
            if DDGS is None:
                return "Web search unavailable."
            with DDGS() as ddgs_client:
                results = []
                # Strategy 1: Text search with cleaned keywords
                try:
                    results = list(ddgs_client.text(kw, max_results=max_results))
                except Exception:
                    pass
                    
                # Strategy 2: News search if news in query
                if not results and ("news" in query.lower() or "headline" in query.lower()):
                    try:
                        results = list(ddgs_client.news(kw, max_results=max_results))
                    except Exception:
                        pass
                        
                # Strategy 3: Raw query text search
                if not results:
                    try:
                        results = list(ddgs_client.text(query, max_results=max_results))
                    except Exception:
                        pass
                    
                if not results:
                    return ""
                    
                formatted = []
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    body = r.get("body", "")
                    date = r.get("date", "")
                    date_str = f" [Date: {date[:10]}]" if date else ""
                    formatted.append(f"{i}. {title}{date_str}\n   {body}")
                return "\n\n".join(formatted)
        except Exception as e:
            logger.warning(f"Web search error: {e}")
            return ""
            
    return await asyncio.to_thread(_do_search)

@router.post("/chat/completions")
async def create_chat_completion(
    request: Request,
    payload: ChatCompletionRequest,
    orchestrator = Depends(get_rabta_orchestrator)
):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
        
    # Extract the latest user query
    user_query = extract_text_content(payload.messages[-1].content)
    
    # Extract auth token from request header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        user_id = auth_header.split(" ")[1]
    else:
        user_id = "open_webui_user"
        
    # Attempt to use a real M2M token if we don't have a valid JWT structure
    if "." not in user_id:
        m2m_token = await get_m2m_token()
        if m2m_token:
            user_id = m2m_token

    gateway = getattr(request.app.state, "gateway", None)
    
    # Classify whether query belongs to [Azm] (Aaram ERP) or [Aalam] (General Knowledge)
    route_info = {"category": "AZM", "id_urn": "urn:aarambooks:intelligence:inventory", "cem_urn": "urn:aarambooks:cem:inventory"}
    if gateway:
        route_info = await classify_query_intent(gateway, user_query)
        
    category = route_info.get("category", "AALAM")
    id_urn = route_info.get("id_urn", "urn:aarambooks:intelligence:inventory")
    cem_urn = route_info.get("cem_urn", "urn:aarambooks:cem:inventory")
        
    if category == "AZM":
        try:
            # Pass to the generic RABTA business boundary
            raw_response = await orchestrator.process_query(
                query=user_query,
                id_urn=id_urn,
                cem_urn=cem_urn,
                auth_context=user_id
            )
            cleaned_resp = clean_agent_tag(str(raw_response))
            response_text = f"🔸 ᴀᴢᴍ ┃ {cleaned_resp}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            response_text = f"🔸 ᴀᴢᴍ ┃ Error processing business query: {str(e)}"
    else:
        try:
            # Check if query requests real-time / current news / weather / web search
            lower_q = user_query.lower()
            needs_search = any(kw in lower_q for kw in ["news", "today", "yesterday", "current", "latest", "weather", "search", "who is the prime minister", "who is the president", "stock price", "trending", "2025", "2026"])
            
            search_context = ""
            if needs_search:
                search_context = await search_live_web(user_query, max_results=5)
                
            if search_context:
                aalam_system_prompt = (
                    "You are Aalam, an AI assistant with live web search capability.\n"
                    "Here is verified real-time search context from the web for the user's question:\n"
                    "---------------------\n"
                    f"{search_context}\n"
                    "---------------------\n"
                    "Use the real-time search context above to provide a complete, direct, accurate answer to the user's question.\n"
                    "Respond in fluent, professional English without prepending any tags like [Aalam]."
                )
            else:
                aalam_system_prompt = (
                    "You are Aalam, an AI assistant running locally on the user's computer. Knowledge cutoff: September 2024.\n"
                    "Provide helpful, accurate answers to questions about history, science, geography, world leaders, and programming.\n"
                    "Respond in fluent English without adding any tags."
                )
                
            history_messages = [
                GatewayMessage(role="system", content=aalam_system_prompt)
            ] + [
                GatewayMessage(role=m.role, content=clean_agent_tag(extract_text_content(m.content)))
                for m in payload.messages if m.role != "system"
            ]
            gen_req = GatewayGenerationRequest(
                messages=history_messages,
                model=settings.stage_r_1_intent_routing_model,
                temperature=payload.temperature or 0.7
            )
            raw_gen = await gateway.generate(gen_req)
            cleaned_gen = clean_agent_tag(raw_gen.content)
            response_text = f"🟢 ᴀᴀʟᴀᴍ ┃ {cleaned_gen}"
        except Exception as e:
            response_text = f"🟢 ᴀᴀʟᴀᴍ ┃ Error generating response: {str(e)}"
        
    # Handle Streaming responses for Chatbox / ChatGPT clients
    if payload.stream:
        async def event_generator():
            chunk_id = f"chatcmpl-{uuid.uuid4()}"
            created_time = int(time.time())
            
            # Send content chunk
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": payload.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": response_text},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Send finish chunk
            finish_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": payload.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(finish_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        created=int(time.time()),
        model=payload.model,
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ]
    )

@router.get("/models")
async def list_models():
    """Provides model discovery for Open WebUI."""
    return {
        "object": "list",
        "data": [
            {
                "id": "rabta",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "aarambooks"
            },
            {
                "id": "aarambooks-brain",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "aarambooks"
            }
        ]
    }
