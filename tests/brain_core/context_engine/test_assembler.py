import pytest
from datetime import datetime, UTC
from src.brain_core.context_engine.assembler import ContextAssembler
from src.brain_core.context_engine.registry import ProviderRegistry, ProviderNotRegisteredError
from src.brain_core.context_engine.schemas import ContextAssemblyRequest, SecurityContext
from src.brain_core.models.contexts import CustomerContext, OrderContext
from src.shared.context_contracts.source import SourceSystem, ContextSource
from src.shared.context_contracts.capability import ProviderCapability

class MockCustomerProvider:
    async def get_customer_context(self, customer_reference: str):
        return CustomerContext(customer_id=customer_reference)

class MockOrderProvider:
    async def get_order_context(self, order_reference: str):
        return OrderContext(order_id=order_reference)

class MockSecurityProvider:
    async def get_security_context(self, user_id: str):
        return SecurityContext(
            user_id=user_id,
            source=ContextSource(source_system_name=SourceSystem.aaram_identity, retrieval_timestamp=datetime.now(UTC))
        )

@pytest.fixture
def registry():
    reg = ProviderRegistry()
    reg.register(SourceSystem.shopdeck, ProviderCapability.CUSTOMER, MockCustomerProvider())
    reg.register(SourceSystem.shopdeck, ProviderCapability.ORDER, MockOrderProvider())
    reg.register(SourceSystem.aaram_identity, ProviderCapability.SECURITY, MockSecurityProvider())
    return reg

@pytest.mark.asyncio
async def test_assembler_successful_fusion(registry):
    assembler = ContextAssembler(registry)
    request = ContextAssemblyRequest(
        user_id="user_123",
        customer_reference="cust_456",
        order_reference="ord_789",
        source_system=SourceSystem.shopdeck
    )

    result = await assembler.assemble_context(request)

    assert result.customer is not None
    assert result.customer.customer_id == "cust_456"
    assert result.order is not None
    assert result.order.order_id == "ord_789"
    assert result.security is not None
    assert result.security.user_id == "user_123"
    assert result.inventory is None
    assert result.fulfillment is None

@pytest.mark.asyncio
async def test_assembler_missing_provider(registry):
    assembler = ContextAssembler(registry)
    # Requesting from amazon, but amazon providers are not registered
    request = ContextAssemblyRequest(
        customer_reference="cust_456",
        source_system=SourceSystem.amazon
    )

    with pytest.raises(ProviderNotRegisteredError):
        await assembler.assemble_context(request)

@pytest.mark.asyncio
async def test_assembler_partial_request(registry):
    assembler = ContextAssembler(registry)
    # Only request security, no source_system for customer/order
    request = ContextAssemblyRequest(
        user_id="user_123"
    )

    result = await assembler.assemble_context(request)

    assert result.security is not None
    assert result.security.user_id == "user_123"
    assert result.customer is None
    assert result.order is None
