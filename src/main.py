from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.shared.config import settings
from src.brain_core.context_engine.router import router as context_router
from src.event_bus.router import router as webhook_router, get_inbound_receiver

# Infrastructure
from src.infrastructure.adapters.litellm_gateway import LiteLLMGatewayAdapter
from src.infrastructure.adapters.postgres_memory import PgVectorMemoryAdapter
from src.infrastructure.adapters.postgres_knowledge import PgVectorKnowledgeAdapter

# Core
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.orchestrator import NDRIntelligenceOrchestrator
from src.event_bus.receiver import InboundReceiver

from src.infrastructure.adapters.httpx_client import HttpxClientAdapter
from src.infrastructure.gateway_config import ConfigDrivenGatewayConfiguration
from src.infrastructure.context_capability_gateway import ContextCapabilityGateway

app = FastAPI(
    title="AaramBooks Brain Core API",
    description="Intelligence foundation and orchestrator for AaramBooks.",
    version="0.1.0",
)

# === COMPOSITION ROOT ===
# 1. Database
engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# 2. Infrastructure Adapters
gateway = LiteLLMGatewayAdapter(base_url=settings.litellm_base_url, api_key=settings.litellm_master_key if hasattr(settings, 'litellm_master_key') else "sk-mock")
memory = PgVectorMemoryAdapter(async_session_factory)
knowledge = PgVectorKnowledgeAdapter(async_session_factory)

# 3. Registry & Context
registry = ProviderRegistry()

# Initialize dynamic capability routing (fallback to standard environment mapping if empty)
if not settings.capability_routes:
    inventory_cem_endpoint = f"{settings.inventory_url.rstrip('/')}/api/v1/context/resolve"
    settings.capability_routes = {
        "urn:aarambooks:inventory:capability:balance": inventory_cem_endpoint,
        "urn:aarambooks:inventory:capability:ledger": inventory_cem_endpoint,
        "urn:aarambooks:inventory:capability:jobwork_status": inventory_cem_endpoint,
        "urn:aarambooks:inventory:capability:exception_status": inventory_cem_endpoint,
    }

# Instantiate Generic Gateway
gateway_config = ConfigDrivenGatewayConfiguration(routing_map=settings.capability_routes)
http_client = HttpxClientAdapter()
capability_gateway = ContextCapabilityGateway(config=gateway_config, http_client=http_client)

# Register Inventory Capabilities
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:balance",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.sku", "inventory.entity.warehouse"},
        supported_constraint_types={"ENTITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:ledger",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.sku", "inventory.entity.posting_date"},
        supported_constraint_types={"ENTITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:jobwork_status",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.jobwork_vendor", "inventory.entity.sku"},
        supported_constraint_types={"ENTITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:exception_status",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.sku", "inventory.entity.exception_date"},
        supported_constraint_types={"ENTITY"}
    ),
    provider=capability_gateway
)

assembler = ContextAssembler(registry)

# 5. Intelligence Orchestrators
cq_orch = CustomerQueryOrchestrator(gateway=gateway, knowledge=knowledge, memory=memory)
ndr_orch = NDRIntelligenceOrchestrator(gateway=gateway, knowledge=knowledge, memory=memory)

# 6. Event Bus
receiver = InboundReceiver(query_orchestrator=cq_orch, ndr_orchestrator=ndr_orch)

# === DEPENDENCY INJECTION OVERRIDES ===
app.dependency_overrides[get_inbound_receiver] = lambda: receiver

# === ROUTERS ===
app.include_router(context_router)
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok", 
        "service": "aarambooks-brain-api", 
        "environment": settings.environment
    }
