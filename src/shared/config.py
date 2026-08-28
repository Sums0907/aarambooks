from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    port: int = 8000
    environment: str = "development"
    database_url: str
    litellm_base_url: str = "http://localhost:4000"
    
    # External Ecosystem
    identity_url: str = "https://api.identity.aarambooks.cloud"
    # ==============================================================================
    # LEGACY COMPATIBILITY
    # These fields are required by surviving legacy Event Bus and NDR adapters.
    # They MUST NOT participate in Stage F ContextCapabilityGateway routing.
    # ==============================================================================
    inventory_url: str = "https://api.inventory.aarambooks.cloud"
    packing_url: str = "https://api.packing.aarambooks.cloud"
    shiprocket_token: str = ""
    shopdeck_token: str = ""
    identity_public_key: str = ""
    brain_client_id: str = ""
    brain_client_secret: str = ""
    capability_routes: dict[str, str] = {}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
