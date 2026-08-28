import pytest
from src.brain_core.context_engine.registry import ProviderRegistry, ProviderNotRegisteredError, DuplicateProviderRegistrationError, CapabilityMetadata

def test_successful_registration_and_lookup():
    registry = ProviderRegistry()
    mock_provider = object()
    metadata = CapabilityMetadata(provides_identities={"customer"}, supported_constraint_types={"ENTITY"})

    registry.register("urn:aaram:mock:capability", metadata, mock_provider)

    resolved = registry.resolve("urn:aaram:mock:capability")
    assert resolved is mock_provider

def test_duplicate_registration_fails():
    registry = ProviderRegistry()
    mock_provider = object()
    metadata = CapabilityMetadata(provides_identities={"customer"}, supported_constraint_types={"ENTITY"})

    registry.register("urn:aaram:mock:capability", metadata, mock_provider)

    with pytest.raises(DuplicateProviderRegistrationError):
        registry.register("urn:aaram:mock:capability", metadata, mock_provider)

def test_missing_provider_fails():
    registry = ProviderRegistry()

    with pytest.raises(ProviderNotRegisteredError):
        registry.resolve("urn:aaram:missing:capability")

def test_multiple_providers_isolation():
    registry = ProviderRegistry()
    mock_provider_1 = object()
    mock_provider_2 = object()
    metadata = CapabilityMetadata(provides_identities={"customer"}, supported_constraint_types={"ENTITY"})

    registry.register("urn:aaram:mock:cap1", metadata, mock_provider_1)
    registry.register("urn:aaram:mock:cap2", metadata, mock_provider_2)

    assert registry.resolve("urn:aaram:mock:cap1") is mock_provider_1
    assert registry.resolve("urn:aaram:mock:cap2") is mock_provider_2
