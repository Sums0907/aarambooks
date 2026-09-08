from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    litellm_base_url: str = "http://localhost:4000"
    litellm_model: str = "gemini/gemini-1.5-pro-latest"
    litellm_api_key: str = "sk-1234"
    llm_enforce_json_format: bool = False
    llm_routing_max_tokens: int = 150
    
    # Stage-Based Multi-LLM Model Routing
    stage_r_1_intent_routing_model: str = "local-qwen"
    stage_r_2_planning_model: str = "local-qwen"
    stage_r_5_entity_resolution_model: str = "local-qwen"
    stage_r_7_response_synthesis_model: str = "local-qwen"
    stage_5_analytics_engine_model: str = "local-qwen"
    stage_6_executive_reports_model: str = "gemini-3.6-flash"
    
    # External Ecosystem
    identity_url: str = "https://api-identity.aarambooks.cloud"
    # ==============================================================================
    # These fields are required by surviving legacy Event Bus and NDR adapters.
    # They MUST NOT participate in Stage F ContextCapabilityGateway routing.
    # ==============================================================================
    inventory_url: str = "https://api-inventory.aarambooks.cloud"
    shopdeck_url: str = "https://api-shopdeck.aarambooks.cloud"
    packing_url: str = "https://api-packing.aarambooks.cloud"
    shiprocket_token: str = ""
    shopdeck_token: str = ""
    shopdeck_ndr_transport: str = "api"
    identity_public_key: str = ""
    brain_client_id: str = ""
    brain_client_secret: str = ""
    capability_routes: dict[str, str] = {}
    
    # Exotel Configuration
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = "api.exotel.com"
    exotel_account_sid: str = ""
    exotel_caller_id: str = ""
    exotel_voicebot_flow_url: str = ""
    # A separate bot's flow URL, created and named independently in the Exotel console
    # (e.g. "Priya_Staging") - Exotel itself has no formal staging/production distinction,
    # so this side of the split lives entirely in Brain's own config. Empty until that
    # second bot is actually created.
    exotel_voicebot_flow_url_staging: str = ""
    exotel_webhook_base_url: str = ""
    aaram_exotel_webhook_secret: str = "default_unsafe_secret_replace_in_prod"
    test_phone_override: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
