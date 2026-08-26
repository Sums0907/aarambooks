from typing import Dict, Tuple, Any
from src.shared.context_contracts.source import SourceSystem
from src.shared.context_contracts.capability import ProviderCapability

class DuplicateProviderRegistrationError(Exception):
    """Raised when a provider is already registered for a given (SourceSystem, Capability)."""
    pass

class ProviderNotRegisteredError(Exception):
    """Raised when a requested provider does not exist in the registry."""
    pass

class ProviderRegistry:
    """
    Generic registry to resolve Business Adapter providers dynamically.
    """
    def __init__(self):
        self._registry: Dict[Tuple[SourceSystem, ProviderCapability], Any] = {}

    def register(self, source_system: SourceSystem, capability: ProviderCapability, provider: Any) -> None:
        key = (source_system, capability)
        if key in self._registry:
            raise DuplicateProviderRegistrationError(
                f"Provider already registered for SourceSystem '{source_system}' and Capability '{capability}'."
            )
        self._registry[key] = provider

    def resolve(self, source_system: SourceSystem, capability: ProviderCapability) -> Any:
        key = (source_system, capability)
        if key not in self._registry:
            raise ProviderNotRegisteredError(
                f"No provider registered for SourceSystem '{source_system}' and Capability '{capability}'."
            )
        return self._registry[key]
