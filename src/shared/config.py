from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    litellm_base_url: str = "http://localhost:4000"
    litellm_model: str = "local-qwen"
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
    # LEGACY COMPATIBILITY
    # These fields are required by surviving legacy Event Bus and NDR adapters.
    # They MUST NOT participate in Stage F ContextCapabilityGateway routing.
    # ==============================================================================
    inventory_url: str = "https://api-inventory.aarambooks.cloud"
    packing_url: str = "https://api-packing.aarambooks.cloud"
    shiprocket_token: str = ""
    shopdeck_token: str = ""
    identity_public_key: str = ""
    brain_client_id: str = ""
    brain_client_secret: str = ""
    capability_routes: dict[str, str] = {}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
