import logging
logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.infrastructure.mongo_client import MongoDBManager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.shared.config import settings
from src.brain_core.context_engine.router import router as context_router
from src.event_bus.router import router as webhook_router, ndr_event_router, get_inbound_receiver, get_communication_engine
from src.api.webhooks.exotel_webhooks import router as exotel_router

# Infrastructure
from src.infrastructure.adapters.litellm_gateway import LiteLLMGatewayAdapter
from src.infrastructure.adapters.postgres_memory import PgVectorMemoryAdapter
from src.infrastructure.adapters.postgres_knowledge import PgVectorKnowledgeAdapter

# Core
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, CapabilityMetadata
from src.intelligence_domains.customer_query.orchestrator import CustomerQueryOrchestrator
from src.intelligence_domains.ndr.communication_engine import CommunicationEngine
from src.intelligence_domains.ndr.communication_repository import CommunicationRepository
from src.intelligence_domains.ndr.reply_parser import CustomerReplyParser
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

# lifespan's shutdown path calls logger.info; without this binding it raises NameError
# and ndr_poller.stop() / gateway.close() / MongoDBManager.disconnect() never run.
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB for NDR communications
    mongo_uri = getattr(settings, "mongo_uri", "mongodb://localhost:27017")
    await MongoDBManager.connect(mongo_uri)

    logging.info("Starting up RabbitMQ connection...")
    # await gateway.connect()
    
    # Start the NDR Queue Consumer
    ndr_poller.start()
    logging.info("Started NDR Queue Poller")

    yield

    # Shutdown
    logger.info("Shutting down NDR Queue Poller...")
    await ndr_poller.stop()
    logger.info("Shutting down RabbitMQ connection...")
    await gateway.close()
    
    # Cleanup
    await MongoDBManager.disconnect()

app = FastAPI(
    title="AaramBooks Brain Core API",
    description="Intelligence foundation and orchestrator for AaramBooks.",
    version="0.1.0",
    lifespan=lifespan
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
from src.azm.provider import AzmProviderFactory
azm_provider = AzmProviderFactory.create()
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
from src.infrastructure.adapters.catalog_cem_adapter import CatalogCemAdapter
from src.infrastructure.adapters.shopdeck_cem_adapter import ShopdeckCemAdapter
from src.shared.rabta_interfaces import IntelligenceDomainResolver, ContextExecutionResolver, IntelligenceDomainProvider, ContextExecutionAdapter


class AppIDResolver(IntelligenceDomainResolver):
    def __init__(self, ids: dict):
        self._ids = ids
    def resolve(self, id_urn: str) -> IntelligenceDomainProvider:
        return self._ids.get(id_urn)

class DummyCEMResolver(ContextExecutionResolver):
    def __init__(self, cems: dict):
        self._cems = cems
    def resolve(self, cem_urn: str) -> ContextExecutionAdapter:
        return self._cems.get(cem_urn)

from src.brain_core.sql.engine import TextToSqlEngine
text_to_sql_engine = TextToSqlEngine(gateway=gateway)

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

catalog_cem = CatalogCemAdapter(database_url=settings.database_url)
shopdeck_cem = ShopdeckCemAdapter(
    base_url=getattr(settings, "shopdeck_url", "http://localhost:8002"),
    identity_url=settings.identity_url,
    client_id=settings.brain_client_id,
    client_secret=settings.brain_client_secret
)

# Register Shopdeck Capabilities
registry.register(
    capability_urn="urn:aarambooks:shopdeck:capability:ndr_details",
    metadata=CapabilityMetadata(
        provides_identities={"ndr.entity.awb", "shopdeck.event.delivery_exception", "shopdeck.entity.shipment"},
        supported_constraint_types={"ENTITY"}
    ),
    provider=shopdeck_cem
)

cem_resolver = DummyCEMResolver({
    "urn:aarambooks:cem:inventory": inventory_cem,
    "urn:aarambooks:cem:ndr": shopdeck_cem,
    "urn:aarambooks:cem:shopdeck": shopdeck_cem,
    "urn:aarambooks:cem:catalog": catalog_cem
})

from src.intelligence_domains.catalog_intelligence.orchestrator import CatalogIntelligenceOrchestrator
catalog_orch = CatalogIntelligenceOrchestrator(
    memory_provider=memory,
    gateway_provider=gateway,
    azm_provider=azm_provider,
    cem_resolver=cem_resolver
)

# 5. Intelligence Orchestrators
cq_orch = CustomerQueryOrchestrator(gateway=gateway, knowledge=knowledge, memory=memory)
ndr_orch = NDRIntelligenceOrchestrator(
    gateway=gateway,
    knowledge=knowledge,
    memory=memory,
    azm_provider=azm_provider
)

id_resolver = AppIDResolver({
    "urn:aarambooks:intelligence:inventory": inventory_orch,
    "urn:aarambooks:intelligence:ndr": ndr_orch,
    "urn:aarambooks:intelligence:catalog": catalog_orch
})

rabta_orch = RabtaOrchestrator(
    id_resolver=id_resolver,
    cem_resolver=cem_resolver,
    classifier=RequirementClassifier(gateway)
)

# Store in app state for the OpenAI adapter
app.state.inventory_orchestrator = inventory_orch
app.state.ndr_orchestrator = ndr_orch
app.state.rabta_orchestrator = rabta_orch
app.state.gateway = gateway

# 6. Event Bus
from src.infrastructure.adapters.customer_engagement.repository import CustomerEngagementRepository
from src.infrastructure.adapters.customer_engagement.exotel_adapter import ExotelVoiceBotAdapter
from src.infrastructure.adapters.customer_engagement.executor import CustomerEngagementExecutor

from src.brain_core.context_engine.ccc_builder import CustomerConversationContextBuilder
ccc_builder = CustomerConversationContextBuilder(provider=shopdeck_cem, inventory_provider=inventory_cem)

comm_repo = CommunicationRepository()
engagement_repo = CustomerEngagementRepository()
exotel_adapter = ExotelVoiceBotAdapter()
executor = CustomerEngagementExecutor(repository=engagement_repo, exotel_adapter=exotel_adapter)

reply_parser = CustomerReplyParser(gateway=gateway)
comm_engine = CommunicationEngine(repository=comm_repo, reply_parser=reply_parser, executor=executor, ccc_builder=ccc_builder)

from src.workers.ndr_queue_poller import NDRQueuePoller
ndr_poller = NDRQueuePoller(shopdeck_adapter=shopdeck_cem, ccc_builder=ccc_builder, comm_engine=comm_engine, orchestrator=ndr_orch, claimer_id=f"sa:{settings.brain_client_id}")
receiver = InboundReceiver(
    query_orchestrator=cq_orch, 
    ndr_orchestrator=ndr_orch,
    communication_engine=comm_engine,
    brain_orchestrator=brain_orch
)

# === DEPENDENCY INJECTION OVERRIDES ===
app.dependency_overrides[get_inbound_receiver] = lambda: receiver
app.dependency_overrides[get_communication_engine] = lambda: comm_engine

# === ROUTERS ===
app.include_router(context_router)
app.include_router(webhook_router)
app.include_router(ndr_event_router)
app.include_router(openai_router)
app.include_router(exotel_router)

from fastapi.responses import FileResponse
from fastapi import HTTPException
import asyncpg
import uuid

@app.get("/api/v1/catalog/artifacts/{artifact_id}/download")
async def download_catalog_artifact(artifact_id: str):
    from business_systems.catalog.service import CatalogService
    
    try:
        parsed_id = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact_id format")
        
    url = settings.database_url.replace("postgresql+asyncpg", "postgresql")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    try:
        service = CatalogService(pool)
        file_path = await service.get_publication_artifact_path(parsed_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="Artifact not found or not committed")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Artifact file missing from disk")
        return FileResponse(file_path, filename=os.path.basename(file_path))
    finally:
        await pool.close()

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok", 
        "service": "aarambooks-brain-api", 
        "environment": settings.environment
    }
