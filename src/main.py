import os
from dotenv import load_dotenv
load_dotenv()

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

from src.brain_core.planning.planner import CognitivePlanner
from src.brain_core.orchestration.resolver import CapabilityResolver
from src.brain_core.semantics.resolver import GenericSemanticResolver
from src.brain_core.orchestration.orchestrator import BrainOrchestrator
from src.intelligence_domains.inventory_intelligence.knowledge import InventorySemanticKnowledge
from src.intelligence_domains.inventory_intelligence.orchestrator import InventoryIntelligenceOrchestrator
from src.interfaces.openai_api import router as openai_router
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
gateway = LiteLLMGatewayAdapter(base_url=settings.litellm_base_url, api_key=getattr(settings, 'litellm_master_key', None))
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
        provides_identities={"inventory.entity.sku", "inventory.entity.warehouse", "inventory.capability.balance"},
        supported_constraint_types={"ENTITY", "CAPABILITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:ledger",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.sku", "inventory.entity.posting_date"},
        supported_constraint_types={"ENTITY", "CAPABILITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:jobwork_status",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.jobwork_vendor", "inventory.entity.sku"},
        supported_constraint_types={"ENTITY", "CAPABILITY"}
    ),
    provider=capability_gateway
)
registry.register(
    capability_urn="urn:aarambooks:inventory:capability:exception_status",
    metadata=CapabilityMetadata(
        provides_identities={"inventory.entity.sku", "inventory.entity.exception_date"},
        supported_constraint_types={"ENTITY", "CAPABILITY"}
    ),
    provider=capability_gateway
)

assembler = ContextAssembler(registry)

# 4. Brain Orchestrator & Inventory Domain
from src.infrastructure.knowledge.azm_provider import InMemoryAzmProvider
azm_provider = InMemoryAzmProvider()
inventory_knowledge = InventorySemanticKnowledge(azm_provider)

planner = CognitivePlanner(gateway=gateway)
cap_resolver = CapabilityResolver(registry)
sem_resolver = GenericSemanticResolver(knowledge=inventory_knowledge)

brain_orch = BrainOrchestrator(
    planner=planner,
    resolver=cap_resolver,
    assembler=assembler,
    semantic_resolver=sem_resolver
)

from src.brain_core.classification.classifier import RequirementClassifier
from src.brain_core.orchestration.rabta_orchestrator import RabtaOrchestrator
from src.infrastructure.adapters.inventory_cem_adapter import InventoryCemAdapter
from src.shared.rabta_interfaces import IntelligenceDomainResolver, ContextExecutionResolver, IntelligenceDomainProvider, ContextExecutionAdapter

class DummyIDResolver(IntelligenceDomainResolver):
    def __init__(self, inventory_id):
        self._id = inventory_id
    def resolve(self, id_urn: str) -> IntelligenceDomainProvider:
        if id_urn == "urn:aarambooks:intelligence:inventory":
            return self._id
        return None

class DummyCEMResolver(ContextExecutionResolver):
    def __init__(self, inventory_cem):
        self._cem = inventory_cem
    def resolve(self, cem_urn: str) -> ContextExecutionAdapter:
        if cem_urn == "urn:aarambooks:cem:inventory":
            return self._cem
        return None

inventory_orch = InventoryIntelligenceOrchestrator(
    brain_orchestrator=brain_orch,
    gateway=gateway,
    knowledge=inventory_knowledge,
    memory=memory
)

inventory_cem = InventoryCemAdapter(
    brain_orchestrator=brain_orch,
    capabilities=inventory_knowledge.get_certified_capabilities()
)

rabta_orch = RabtaOrchestrator(
    id_resolver=DummyIDResolver(inventory_orch),
    cem_resolver=DummyCEMResolver(inventory_cem),
    classifier=RequirementClassifier(gateway)
)

# Store in app state for the OpenAI adapter
app.state.inventory_orchestrator = inventory_orch
app.state.rabta_orchestrator = rabta_orch
app.state.gateway = gateway

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
app.include_router(openai_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok", 
        "service": "aarambooks-brain-api", 
        "environment": settings.environment
    }
