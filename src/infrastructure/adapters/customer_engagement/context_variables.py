from typing import Any, Dict, Optional


# Provider-agnostic configuration for voicebot variables and instructions.
# Both the allow-list (which projection fields reach the bot) and the instruction_* strings
# (the safety/behavioral rules injected alongside them) live in
# src/config/voicebot_variables/ as JSON files, one per domain. Any voice provider
# (Exotel, Sarvam, or future) reads from exactly these files. A field or instruction
# added to the JSON reaches every provider automatically; anything missing reaches none
# of them — so this is the single place to update when the bot's context changes.
import json
import importlib.resources
from src.shared.domain_contracts import IntelligenceDomain

_CONFIG_CACHE: Dict[str, list] = {}
_INSTRUCTIONS_CACHE: Dict[str, Dict[str, str]] = {}

def _get_context_keys_for_domain(domain: IntelligenceDomain) -> list:
    if domain.value in _CONFIG_CACHE:
        return _CONFIG_CACHE[domain.value]
    
    config_filename = f"{domain.value}_voicebot_context_variables.json"
    
    try:
        config_text = importlib.resources.read_text("src.config.voicebot_variables", config_filename)
    except FileNotFoundError:
        raise FileNotFoundError(f"Voicebot configuration missing for domain: {domain.value}")
        
    keys = json.loads(config_text)
    
    if not isinstance(keys, list):
        raise TypeError(f"Expected a JSON list in {config_filename}, got {type(keys)}")
    
    _CONFIG_CACHE[domain.value] = keys
    return keys


def get_instructions_for_domain(domain: IntelligenceDomain) -> Dict[str, str]:
    """
    Returns the provider-agnostic instruction_* dict for a domain.
    Loaded from src/config/voicebot_variables/<domain>_voicebot_instructions.json.
    Any voice provider (Exotel, Sarvam, etc.) calls this instead of hardcoding
    instruction strings in provider-specific webhook handlers.
    """
    if domain.value in _INSTRUCTIONS_CACHE:
        return _INSTRUCTIONS_CACHE[domain.value]

    config_filename = f"{domain.value}_voicebot_instructions.json"

    try:
        config_text = importlib.resources.read_text("src.config.voicebot_variables", config_filename)
    except FileNotFoundError:
        raise FileNotFoundError(f"Voicebot instructions config missing for domain: {domain.value}")

    instructions = json.loads(config_text)

    if not isinstance(instructions, dict):
        raise TypeError(f"Expected a JSON object in {config_filename}, got {type(instructions)}")

    _INSTRUCTIONS_CACHE[domain.value] = instructions
    return instructions

def build_provider_call_variables(
    engagement_id: str,
    action_request_id: Optional[str],
    engagement: Dict[str, Any],
    domain: IntelligenceDomain,
) -> Dict[str, str]:
    """
    Builds the flat, provider-agnostic string-keyed variable dict every voice provider gets
    for a call, loading the allow-list dynamically based on the IntelligenceDomain.
    """
    variables: Dict[str, str] = {
        "brand_name": "Aaram Homes",
        "engagement_id": str(engagement_id),
    }
    if action_request_id:
        variables["action_request_id"] = str(action_request_id)

    if engagement.get("awb_no") and engagement.get("awb_no") != "UNKNOWN":
        variables["awb_no"] = str(engagement["awb_no"])

    call_context = engagement.get("call_context", {}) or {}
    allowed_keys = _get_context_keys_for_domain(domain)
    
    for key in allowed_keys:
        if call_context.get(key) is not None:
            value = call_context[key]
            variables[key] = ", ".join(value) if isinstance(value, list) else str(value)

    return variables
