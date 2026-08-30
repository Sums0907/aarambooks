---
description: Strict rule against hardcoding model-specific logic in core application code.
---

# Model Independence Rule

**CRITICAL RULE:** Do NOT hardcode model-specific configurations, hacks, or behaviors directly into the main application code (e.g., `if "qwen" in model_name:`, hardcoded `max_tokens` fallbacks, or model-specific prompt string manipulation).

## Guidelines:
1. **Generic Basecode:** Core logic, orchestrators, and adapters (like `LiteLLMGatewayAdapter`) must remain strictly generic and model-agnostic.
2. **Configuration Driven:** If a specific model requires special handling (e.g., forcing JSON format, custom stop sequences, specific token limits), define these in:
   - Environment variables (`.env`).
   - A dedicated configuration file (e.g., `model_profiles.py` or a YAML registry) that maps model names to their specific capabilities and constraints.
3. **Capabilities over Names:** When adapting behavior, check for *capabilities* passed via configuration (e.g., `config.supports_native_json`) rather than checking the model name directly in the execution path.
