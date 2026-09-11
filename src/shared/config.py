from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    # main.py's lifespan reads this via getattr(settings, "mongo_uri", ...) - without a
    # declared field here, pydantic-settings has nothing to populate from MONGO_URI, so that
    # getattr always silently fell through to its localhost default regardless of what was
    # set in the environment. Any deployment where Mongo isn't reachable at localhost:27017
    # from Brain's own process (e.g. a separate container) needs this actually wired.
    mongo_uri: str = "mongodb://localhost:27017"
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
    # Catalog BS - reached only over HTTP as of the catalog_cem_adapter.py HTTP-boundary
    # rewrite. Localhost default matches local dev (business_systems/catalog/api.py running
    # standalone); production must point at wherever Catalog is actually deployed.
    catalog_url: str = "http://localhost:8300"
    catalog_internal_token: str = ""
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

    # Sarvam Configuration (voice bot migration - see docs/claude/)
    # sarvam_app_version=4 is currently a DRAFT ("in-progress edits, not yet live" per
    # Sarvam's own docs) - the user is still editing it and has not committed it. Real test
    # calls should wait until it's committed to a real version number; update this value
    # then. Do not assume a draft version is callable via Instant Outbound - unconfirmed
    # either way in public docs.
    sarvam_app_version: int = 4
    # sarvam_api_key is a Voice Agents key specifically - separate from Sarvam's standard
    # TTS/STT API keys, per Sarvam's own docs. Don't reuse a standard API key here.
    sarvam_api_key: str = ""
    sarvam_webhook_secret: str = ""
    sarvam_org_id: str = "01a08c70-379c-7c1b-9877-f5126093cd4a"
    sarvam_workspace_id: str = "01a08c70-37a9-7673-8463-eaaa05417451"
    sarvam_agent_id: str = ""
    sarvam_connection_id: str = ""
    sarvam_phone_number: str = "+918065383367"
    # Used to build webhook_config.url for Instant Outbound's completion webhook - Sarvam
    # calls Brain from outside, same purpose as exotel_webhook_base_url. No Request object
    # is available at dispatch time (this fires from the NDR queue poller's background
    # flow, not inside an HTTP handler), so unlike Exotel's get_webhook_base_url() this
    # can't be derived from request headers - it must be set explicitly.
    sarvam_webhook_base_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
