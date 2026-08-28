from typing import Optional, Dict
from src.shared.context_contracts.capability import CapabilityURN
from src.infrastructure.context_capability_gateway import GatewayConfiguration

class ConfigDrivenGatewayConfiguration(GatewayConfiguration):
    """
    Domain-neutral implementation of GatewayConfiguration.
    Dynamically maps supported Capability URNs to their respective physical Business System CEM endpoints
    using configuration rather than hardcoded logic.
    """
    def __init__(self, routing_map: Dict[str, str]):
        self._routing = routing_map

    def get_endpoint(self, urn: CapabilityURN) -> Optional[str]:
        return self._routing.get(urn)
