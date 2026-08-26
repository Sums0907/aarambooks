import pytest
from src.brain_core.context_engine.registry import ProviderRegistry, ProviderNotRegisteredError, DuplicateProviderRegistrationError
from src.shared.context_contracts.source import SourceSystem
from src.shared.context_contracts.capability import ProviderCapability

def test_successful_registration_and_lookup():
    registry = ProviderRegistry()
    mock_provider = object()

    registry.register(SourceSystem.shopdeck, ProviderCapability.CUSTOMER, mock_provider)

    resolved = registry.resolve(SourceSystem.shopdeck, ProviderCapability.CUSTOMER)
    assert resolved is mock_provider

def test_duplicate_registration_fails():
    registry = ProviderRegistry()
    mock_provider = object()

    registry.register(SourceSystem.shopdeck, ProviderCapability.CUSTOMER, mock_provider)

    with pytest.raises(DuplicateProviderRegistrationError):
        registry.register(SourceSystem.shopdeck, ProviderCapability.CUSTOMER, mock_provider)

def test_missing_provider_fails():
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotRegisteredError):
        registry.resolve(SourceSystem.amazon, ProviderCapability.ORDER)

def test_multiple_providers_isolation():
    registry = ProviderRegistry()
    mock_provider_1 = object()
    mock_provider_2 = object()

    registry.register(SourceSystem.shopdeck, ProviderCapability.CUSTOMER, mock_provider_1)
    registry.register(SourceSystem.amazon, ProviderCapability.CUSTOMER, mock_provider_2)

    assert registry.resolve(SourceSystem.shopdeck, ProviderCapability.CUSTOMER) is mock_provider_1
    assert registry.resolve(SourceSystem.amazon, ProviderCapability.CUSTOMER) is mock_provider_2
