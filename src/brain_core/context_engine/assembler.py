import asyncio
from datetime import datetime, UTC
from src.brain_core.context_engine.schemas import ContextAssemblyRequest, AssembledContext
from src.brain_core.context_engine.registry import ProviderRegistry
from src.shared.context_contracts.capability import ProviderCapability
from src.shared.context_contracts.source import SourceSystem

class ContextAssembler:
    """
    Context Assembler is responsible for assembling contextual snapshots from authoritative business systems and internal intelligence state to provide a grounded context for AI reasoning.
    """

    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    async def assemble_context(self, request: ContextAssemblyRequest) -> AssembledContext:
        customer_ctx = None
        order_ctx = None
        security_ctx = None
        intelligence_ctx = None

        tasks = []

        async def fetch_customer():
            nonlocal customer_ctx
            if request.source_system and request.customer_reference:
                provider = self._registry.resolve(request.source_system, ProviderCapability.CUSTOMER)
                customer_ctx = await provider.get_customer_context(request.customer_reference)

        async def fetch_order():
            nonlocal order_ctx
            if request.source_system and request.order_reference:
                provider = self._registry.resolve(request.source_system, ProviderCapability.ORDER)
                order_ctx = await provider.get_order_context(request.order_reference)

        async def fetch_security():
            nonlocal security_ctx
            if request.user_id:
                provider = self._registry.resolve(SourceSystem.aaram_identity, ProviderCapability.SECURITY)
                security_ctx = await provider.get_security_context(request.user_id)

        async def fetch_intelligence():
            nonlocal intelligence_ctx
            if request.session_id:
                provider = self._registry.resolve(SourceSystem.memory_framework, ProviderCapability.INTELLIGENCE)
                intelligence_ctx = await provider.get_intelligence_context(request.session_id)

        tasks = [
            fetch_customer(),
            fetch_order(),
            fetch_security(),
            # fetch_intelligence() - if memory_framework Capability existed, but let's stick to what's defined in ProviderCapability enum.
        ]

        # We don't have INTELLIGENCE in ProviderCapability enum yet. So we skip memory.
        # Wait, the ProviderCapability enum has: CUSTOMER, ORDER, INVENTORY, FULFILLMENT, SECURITY.
        # Memory is not there. The prompt said: "Do not implement Memory..."

        # Wait, the prompt says "Do not silently swallow missing-provider errors."
        # The registry.resolve will raise ProviderNotRegisteredError if the provider doesn't exist.
        # This is expected behavior and we let it propagate.

        await asyncio.gather(*tasks)

        return AssembledContext(
            security=security_ctx,
            customer=customer_ctx,
            order=order_ctx,
            inventory=None,
            fulfillment=None,
            intelligence=None,
            assembled_at=datetime.now(UTC)
        )
