from typing import Dict, Any, List, Set
from pydantic import BaseModel
from src.shared.context_contracts.capability import CapabilityURN

class DuplicateProviderRegistrationError(Exception):
    """Raised when a provider is already registered for a given Capability URN."""
    pass

class ProviderNotRegisteredError(Exception):
    """Raised when a requested provider does not exist in the registry."""
    pass

class CapabilityMetadata(BaseModel):
    provides_identities: Set[str]
    supported_constraint_types: Set[str]

class ProviderRegistry:
    """
    Generic registry to resolve Context Capability modules dynamically using opaque routing.
    """
    def __init__(self):
        # Maps Capability URN to (Metadata, ProviderInstance)
        self._registry: Dict[CapabilityURN, tuple[CapabilityMetadata, Any]] = {}

    def register(self, capability_urn: CapabilityURN, metadata: CapabilityMetadata, provider: Any) -> None:
        if capability_urn in self._registry:
            raise DuplicateProviderRegistrationError(
                f"Provider already registered for Capability URN '{capability_urn}'."
            )
        self._registry[capability_urn] = (metadata, provider)

    def resolve(self, capability_urn: CapabilityURN) -> Any:
        if capability_urn not in self._registry:
            raise ProviderNotRegisteredError(
                f"No provider registered for Capability URN '{capability_urn}'."
            )
        return self._registry[capability_urn][1]

    def get_all_metadata(self) -> Dict[CapabilityURN, CapabilityMetadata]:
        return {urn: meta for urn, (meta, _) in self._registry.items()}
